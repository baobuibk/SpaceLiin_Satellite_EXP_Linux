// SPDX-License-Identifier: GPL-2.0
/*
 * Hybrid RPMSG Driver: Command Execution + Large File Transfer
 * - Commands via RPMSG
 * - Large files via shared DMA buffer (128MB)
 */

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/rpmsg.h>
#include <linux/slab.h>
#include <linux/tty.h>
#include <linux/tty_driver.h>
#include <linux/tty_flip.h>
#include <linux/io.h>
#include <linux/of.h>
#include <linux/of_reserved_mem.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/poll.h>

#define RPMSG_MAX_SIZE  256
#define DMA_BUFFER_SIZE 0x8000000  /* 128MB */

#define MSG		        "HelloM33\r"

/* Protocol definitions */
#define CMD_TYPE_NORMAL_REQ     0x23  /* Regular command request [#] */
#define CMD_TYPE_FILE_REQ       0x24  /* File transfer request [$] */

#define CMD_TYPE_NORMAL_RESP    0x2D  /* Regular command response [-]*/
#define CMD_TYPE_FILE_RESP      0x3D  /* File transfer response [=]*/

#define REMOTE_CALL_TARGET      0x33
#define REMOTE_CALL_MY_ADDR     0x55

struct cmd_header {
    uint8_t target;
    uint8_t type;
    uint8_t reserved;
    uint16_t length;
} __attribute__((packed));

struct file_transfer_msg {
    uint8_t target;
    uint8_t type;           /* CMD_TYPE_FILE */
    uint8_t flags;
    uint16_t reserved;
    uint32_t offset;        /* Offset in DMA buffer */
    uint32_t size;          /* Data size */
    char filename[240];     /* Keep total 256 bytes */
} __attribute__((packed));

struct rpmsgtty_dma_port {
    /* TTY */
    struct tty_port port;
    struct tty_driver *tty_driver;
    spinlock_t rx_lock;
    
    /* RPMSG */
    struct rpmsg_device *rpdev;
    
    void __iomem *dma_vaddr;
    phys_addr_t dma_paddr;
    size_t dma_size;
    
    struct cdev cdev;
    dev_t devt;
    struct class *class;
    
    struct mutex file_lock;
    wait_queue_head_t file_wait;
    struct file_transfer_msg pending_file;
    bool file_ready;
};

static int map_dma_buffer(struct rpmsgtty_dma_port *cport)
{
    struct device_node *np;
    struct reserved_mem *rmem;
    
    np = of_find_node_by_name(NULL, "rpmsg-dma");
    if (np) {
        rmem = of_reserved_mem_lookup(np);
        if (rmem) {
            cport->dma_paddr = rmem->base;
            cport->dma_size = rmem->size;
        }
        of_node_put(np);
    }
    
    /* Fallback */
    if (!cport->dma_paddr) {
        cport->dma_paddr = 0xa4220000;
        cport->dma_size = DMA_BUFFER_SIZE;
    }
    
    cport->dma_vaddr = ioremap_wc(cport->dma_paddr, cport->dma_size);
    if (!cport->dma_vaddr) {
        pr_err("Failed to map DMA buffer\n");
        return -ENOMEM;
    }
    
    pr_info("DMA buffer: paddr=0x%llx, vaddr=%p, size=%zu MB\n",
            (u64)cport->dma_paddr, cport->dma_vaddr, 
            cport->dma_size / (1024*1024));
    
    return 0;
}

static int rpmsg_hybrid_cb(struct rpmsg_device *rpdev, void *data, int len,
                           void *priv, u32 src)
{
    struct rpmsgtty_dma_port *cport = dev_get_drvdata(&rpdev->dev);
    struct cmd_header *hdr = (struct cmd_header *)data;
    struct file_transfer_msg *file_msg;
    char *payload;
    int payload_len;
    int space;
    unsigned char *cbuf;
    
    if (len < sizeof(struct cmd_header)) {
        dev_err(&rpdev->dev, "Invalid message length\n");
        return -EINVAL;
    }
    
    payload = (char *)data + sizeof(struct cmd_header);
    payload_len = len - sizeof(struct cmd_header);

    if (hdr->target != REMOTE_CALL_MY_ADDR) {
        dev_warn(&rpdev->dev, "Message not for us (target=0x%x)\n", hdr->target);
        return -EINVAL;
    }

    switch (hdr->type) {
    case CMD_TYPE_NORMAL_REQ:
        dev_info(&rpdev->dev, "Command from M33: %.*s\n", payload_len, payload);
        
        spin_lock_bh(&cport->rx_lock);
        space = tty_prepare_flip_string(&cport->port, &cbuf, payload_len);
        if (space > 0) {
            memcpy(cbuf, payload, payload_len);
            tty_flip_buffer_push(&cport->port);
        }
        spin_unlock_bh(&cport->rx_lock);
        break;
        
    case CMD_TYPE_NORMAL_RESP:
        dev_info(&rpdev->dev, "Response from M33: %.*s\n", payload_len, payload);
        
        spin_lock_bh(&cport->rx_lock);
        space = tty_prepare_flip_string(&cport->port, &cbuf, payload_len);
        if (space > 0) {
            memcpy(cbuf, payload, payload_len);
            tty_flip_buffer_push(&cport->port);
        }
        spin_unlock_bh(&cport->rx_lock);
        break;
        
    case CMD_TYPE_FILE_REQ:
        file_msg = (struct file_transfer_msg *)data;
        
        dev_info(&rpdev->dev, "File: %s, offset=0x%x, size=%u\n",
                 file_msg->filename, file_msg->offset, file_msg->size);
        
        /* Validate */
        if (file_msg->offset + file_msg->size > cport->dma_size) {
            dev_err(&rpdev->dev, "Invalid file parameters\n");
            return -EINVAL;
        }
        
        mutex_lock(&cport->file_lock);
        memcpy(&cport->pending_file, file_msg, sizeof(*file_msg));
        cport->file_ready = true;
        wake_up_interruptible(&cport->file_wait);
        mutex_unlock(&cport->file_lock);
        
        dev_info(&rpdev->dev, "Notify file transfer ready to Chardev\n");
        break;
        
    default:
        dev_warn(&rpdev->dev, "Unknown command type: 0x%x\n", hdr->type);
        break;
    }
    
    return 0;
}

/* ==================== TTY Operations ==================== */

static struct tty_port_operations rpmsgtty_port_ops = { };

static int rpmsgtty_install(struct tty_driver *driver, struct tty_struct *tty)
{
    struct rpmsgtty_dma_port *cport = driver->driver_state;
    return tty_port_install(&cport->port, driver, tty);
}

static int rpmsgtty_open(struct tty_struct *tty, struct file *filp)
{
    return tty_port_open(tty->port, tty, filp);
}

static void rpmsgtty_close(struct tty_struct *tty, struct file *filp)
{
    tty_port_close(tty->port, tty, filp);
}

static int rpmsgtty_write(struct tty_struct *tty, const unsigned char *buf,
                          int total)
{
    int count, ret = 0;
    const unsigned char *tbuf = buf;
    struct rpmsgtty_dma_port *cport = container_of(tty->port,
            struct rpmsgtty_dma_port, port);
    struct rpmsg_device *rpdev = cport->rpdev;
    struct cmd_header hdr;
    uint8_t msg_buf[RPMSG_MAX_SIZE];

    if (!buf || total <= 0)
        return -ENOMEM;

    uint8_t cmd_type = CMD_TYPE_NORMAL_REQ;

    if (tbuf[0] == '#') {
        cmd_type = CMD_TYPE_NORMAL_REQ;
        tbuf++; total--;
    } else if (tbuf[0] == '$') {
        cmd_type = CMD_TYPE_FILE_REQ;
        tbuf++; total--;
    } else if (tbuf[0] == '-') {
        cmd_type = CMD_TYPE_NORMAL_RESP;
        tbuf++; total--;
    } else if (tbuf[0] == '=') {
        cmd_type = CMD_TYPE_FILE_RESP;
        tbuf++; total--;
    }

    count = total;

    do {
        int chunk = min(count, (int)(RPMSG_MAX_SIZE - sizeof(hdr)));

        hdr.target = REMOTE_CALL_TARGET;
        hdr.type = cmd_type;
        hdr.reserved = 0;
        hdr.length = chunk;

        memcpy(msg_buf, &hdr, sizeof(hdr));
        memcpy(msg_buf + sizeof(hdr), tbuf, chunk);

        ret = rpmsg_send(rpdev->ept, msg_buf, sizeof(hdr) + chunk);
        if (ret) {
            dev_err(&rpdev->dev, "rpmsg_send failed: %d\n", ret);
            return ret;
        }

        if (count > chunk) {
            count -= chunk;
            tbuf += chunk;
        } else {
            count = 0;
        }

    } while (count > 0);

    return total;
}

static unsigned int rpmsgtty_write_room(struct tty_struct *tty)
{
    return RPMSG_MAX_SIZE;
}

static const struct tty_operations rpmsgtty_ops = {
    .install    = rpmsgtty_install,
    .open       = rpmsgtty_open,
    .close      = rpmsgtty_close,
    .write      = rpmsgtty_write,
    .write_room = rpmsgtty_write_room,
};

/* ==================== Character Device for DMA ==================== */

static int rpmsg_dma_open(struct inode *inode, struct file *filp)
{
    struct rpmsgtty_dma_port *cport = container_of(inode->i_cdev,
                                        struct rpmsgtty_dma_port, cdev);
    filp->private_data = cport;
    return 0;
}

static int rpmsg_dma_release(struct inode *inode, struct file *filp)
{
    return 0;
}

/* Read file transfer notifications */
static ssize_t rpmsg_dma_read(struct file *filp, char __user *buf,
                              size_t count, loff_t *ppos)
{
    struct rpmsgtty_dma_port *cport = filp->private_data;
    struct file_transfer_msg msg;
    int ret;
    
    if (count < sizeof(msg))
        return -EINVAL;
    
    /* Wait for file notification */
    if (filp->f_flags & O_NONBLOCK) {
        if (!cport->file_ready)
            return -EAGAIN;
    } else {
        ret = wait_event_interruptible(cport->file_wait, 
                                        cport->file_ready);
        if (ret)
            return ret;
    }
    
    mutex_lock(&cport->file_lock);
    if (!cport->file_ready) {
        mutex_unlock(&cport->file_lock);
        return -EAGAIN;
    }
    
    memcpy(&msg, &cport->pending_file, sizeof(msg));
    cport->file_ready = false;
    mutex_unlock(&cport->file_lock);
    
    if (copy_to_user(buf, &msg, sizeof(msg)))
        return -EFAULT;
    
    return sizeof(msg);
}

/* IOCTL commands */
#define RPMSG_IOC_MAGIC 'R'
#define RPMSG_GET_DMA_INFO    _IOR(RPMSG_IOC_MAGIC, 1, struct dma_info)
#define RPMSG_READ_DMA_DATA   _IOW(RPMSG_IOC_MAGIC, 2, struct dma_read_req)

struct dma_info {
    uint64_t phys_addr;
    uint64_t size;
};

struct dma_read_req {
    uint32_t offset;
    uint32_t size;
    void __user *buffer;
};

static long rpmsg_dma_ioctl(struct file *filp, unsigned int cmd,
                            unsigned long arg)
{
    struct rpmsgtty_dma_port *cport = filp->private_data;
    
    switch (cmd) {
    case RPMSG_GET_DMA_INFO: {
        struct dma_info info;
        info.phys_addr = cport->dma_paddr;
        info.size = cport->dma_size;
        
        if (copy_to_user((void __user *)arg, &info, sizeof(info)))
            return -EFAULT;
        return 0;
    }
    
    case RPMSG_READ_DMA_DATA: {
        struct dma_read_req req;
        
        if (copy_from_user(&req, (void __user *)arg, sizeof(req)))
            return -EFAULT;
        
        if (req.offset + req.size > cport->dma_size)
            return -EINVAL;
        
        if (copy_to_user(req.buffer, cport->dma_vaddr + req.offset, req.size))
            return -EFAULT;
        
        return 0;
    }
    
    default:
        return -ENOTTY;
    }
}

/* mmap DMA buffer */
static int rpmsg_dma_mmap(struct file *filp, struct vm_area_struct *vma)
{
    struct rpmsgtty_dma_port *cport = filp->private_data;
    unsigned long size = vma->vm_end - vma->vm_start;
    
    if (size > cport->dma_size)
        return -EINVAL;
    
    vma->vm_page_prot = pgprot_writecombine(vma->vm_page_prot);
    
    if (remap_pfn_range(vma, vma->vm_start,
                       cport->dma_paddr >> PAGE_SHIFT,
                       size, vma->vm_page_prot))
        return -EAGAIN;
    
    return 0;
}

/* poll support */
static __poll_t rpmsg_dma_poll(struct file *filp, poll_table *wait)
{
    struct rpmsgtty_dma_port *cport = filp->private_data;
    __poll_t mask = 0;
    
    poll_wait(filp, &cport->file_wait, wait);
    
    if (cport->file_ready)
        mask |= POLLIN | POLLRDNORM;
    
    return mask;
}

static const struct file_operations rpmsg_dma_fops = {
    .owner          = THIS_MODULE,
    .open           = rpmsg_dma_open,
    .release        = rpmsg_dma_release,
    .read           = rpmsg_dma_read,
    .unlocked_ioctl = rpmsg_dma_ioctl,
    .mmap           = rpmsg_dma_mmap,
    .poll           = rpmsg_dma_poll,
};

/* ==================== Probe & Remove ==================== */

static int rpmsg_hybrid_probe(struct rpmsg_device *rpdev)
{
    struct rpmsgtty_dma_port *cport;
    struct tty_driver *tty_driver;
    int ret;
    
    dev_info(&rpdev->dev, "--> [RPMSG/rpmsg] [HieuCao Kernel Module Probing ver 2.0.0 ...] ");
    dev_info(&rpdev->dev, "Hybrid RPMSG probe: 0x%x -> 0x%x\n",
             rpdev->src, rpdev->dst);
    
    cport = devm_kzalloc(&rpdev->dev, sizeof(*cport), GFP_KERNEL);
    if (!cport)
        return -ENOMEM;
    
    cport->rpdev = rpdev;
    spin_lock_init(&cport->rx_lock);
    mutex_init(&cport->file_lock);
    init_waitqueue_head(&cport->file_wait);
    
    /* Map DMA buffer */
    ret = map_dma_buffer(cport);
    if (ret)
        return ret;
    
    /* Setup TTY for commands */
    tty_driver = tty_alloc_driver(1, TTY_DRIVER_UNNUMBERED_NODE);
    if (IS_ERR(tty_driver))
        return PTR_ERR(tty_driver);
    
    tty_driver->driver_name = "rpmsg_hybrid";
    tty_driver->name = kasprintf(GFP_KERNEL, "ttyRPMSG%d", rpdev->dst);
    tty_driver->major = UNNAMED_MAJOR;
    tty_driver->type = TTY_DRIVER_TYPE_CONSOLE;
    tty_driver->init_termios = tty_std_termios;
    
    tty_set_operations(tty_driver, &rpmsgtty_ops);
    tty_port_init(&cport->port);
    cport->port.ops = &rpmsgtty_port_ops;
    cport->tty_driver = tty_driver;
    tty_driver->driver_state = cport;
    
    ret = tty_register_driver(tty_driver);
    if (ret < 0) {
        pr_err("Failed to register TTY driver\n");
        goto err_tty;
    }
    
    /* Setup character device for DMA */
    ret = alloc_chrdev_region(&cport->devt, 0, 1, "rpmsg_dma");
    if (ret)
        goto err_chrdev;
    
    cdev_init(&cport->cdev, &rpmsg_dma_fops);
    cport->cdev.owner = THIS_MODULE;
    
    ret = cdev_add(&cport->cdev, cport->devt, 1);
    if (ret)
        goto err_cdev;
    
    cport->class = class_create(THIS_MODULE, "rpmsg_hybrid");
    if (IS_ERR(cport->class)) {
        ret = PTR_ERR(cport->class);
        goto err_class;
    }
    
    device_create(cport->class, NULL, cport->devt, NULL, "rpmsg_dma%d", rpdev->dst);
    
    dev_set_drvdata(&rpdev->dev, cport);
    
    pr_info("Hybrid RPMSG ready:\n");
    pr_info("  TTY: %s (commands)\n", tty_driver->name);
    pr_info("  DMA: /dev/rpmsg_dma%d (files)\n", rpdev->dst);
    
	ret = rpmsg_send(rpdev->ept, MSG, strlen(MSG));
	if (ret) {
		dev_err(&rpdev->dev, "rpmsg_send failed: %d\n", ret);
		goto err_tty;
	} else {
        dev_info(&rpdev->dev, "Sent message to remote: %s\n", MSG);
    }

    return 0;

err_class:
    cdev_del(&cport->cdev);
err_cdev:
    unregister_chrdev_region(cport->devt, 1);
err_chrdev:
    tty_unregister_driver(tty_driver);
err_tty:
    tty_driver_kref_put(tty_driver);
    iounmap(cport->dma_vaddr);
    return ret;
}

static void rpmsg_hybrid_remove(struct rpmsg_device *rpdev)
{
    struct rpmsgtty_dma_port *cport = dev_get_drvdata(&rpdev->dev);
    
    device_destroy(cport->class, cport->devt);
    class_destroy(cport->class);
    cdev_del(&cport->cdev);
    unregister_chrdev_region(cport->devt, 1);
    
    tty_unregister_driver(cport->tty_driver);
    kfree(cport->tty_driver->name);
    tty_driver_kref_put(cport->tty_driver);
    tty_port_destroy(&cport->port);
    
    iounmap(cport->dma_vaddr);
    
    dev_info(&rpdev->dev, "Hybrid RPMSG removed\n");
}

static struct rpmsg_device_id rpmsg_hybrid_id_table[] = {
    { .name = "rpmsg-openamp-demo-channel" },
    { .name	= "rpmsg-virtual-tty-channel-1" },
	{ .name	= "rpmsg-virtual-tty-channel" },
    { .name = "rpmsg-hybrid-channel" },
    { },
};

static struct rpmsg_driver rpmsg_hybrid_driver = {
    .drv.name   = KBUILD_MODNAME,
    .drv.owner  = THIS_MODULE,
    .id_table   = rpmsg_hybrid_id_table,
    .probe      = rpmsg_hybrid_probe,
    .callback   = rpmsg_hybrid_cb,
    .remove     = rpmsg_hybrid_remove,
};

module_rpmsg_driver(rpmsg_hybrid_driver);

MODULE_DESCRIPTION("Hybrid RPMSG: Commands + Large File Transfer");
MODULE_LICENSE("GPL v2");
