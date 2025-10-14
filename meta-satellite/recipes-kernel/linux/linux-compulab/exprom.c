/*
 * exprom-i2c-slave driver for IMX93
 * Version: 2.0.0
 * Author: Cao Hieu
 */
#include <linux/bitfield.h>
#include <linux/i2c.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/sysfs.h>
#include <linux/vmalloc.h>
#include <linux/uaccess.h>

#define MAX_FILE_SIZE (48 * 1024 * 1024)    // 48MB
#define NUM_ADDRESS_BYTES 4                 // 32-bit addressing

struct file_slave_data {
	struct bin_attribute bin;
	spinlock_t buffer_lock;
	u32 current_offset;                     // Current read/write position
	u32 file_size;                          // Actual file size loaded
	u8 address_bytes[4];                    // Buffer for receiving 4-byte address
	u8 addr_byte_count;                     // Counter for address bytes received
	bool address_set;                       // Flag: address fully received
	u8 *file_buffer;                        // Large buffer for file content (vmalloc)
    unsigned long total_reads;              // Statistics: total read operations
	unsigned long total_writes;             // Statistics: total write operations
	unsigned long last_load_size;           // Size of last loaded file
};

static int i2c_slave_file_slave_cb(struct i2c_client *client,
				   enum i2c_slave_event event, u8 *val)
{
	struct file_slave_data *fdata = i2c_get_clientdata(client);
	u32 offset;

	switch (event) {
	case I2C_SLAVE_WRITE_RECEIVED:
		/* Receiving address bytes: ADDR_H0, ADDR_H1, ADDR_L0, ADDR_L1 */
		if (fdata->addr_byte_count < NUM_ADDRESS_BYTES) {
			fdata->address_bytes[fdata->addr_byte_count] = *val;
			fdata->addr_byte_count++;
			
			/* All 4 address bytes received */
			if (fdata->addr_byte_count == NUM_ADDRESS_BYTES) {
				/* Reconstruct 32-bit offset from 4 bytes (Big Endian) */
				offset = ((u32)fdata->address_bytes[0] << 24) |
					 ((u32)fdata->address_bytes[1] << 16) |
					 ((u32)fdata->address_bytes[2] << 8)  |
					 ((u32)fdata->address_bytes[3]);
				
				spin_lock(&fdata->buffer_lock);
				fdata->current_offset = offset;
				fdata->address_set = true;
				spin_unlock(&fdata->buffer_lock);
				
				dev_info(&client->dev, "Offset set to: 0x%08X (%u)\n", 
					offset, offset);
			}
		} else {
			/* Additional writes after address - could be used for write operation */
			dev_info(&client->dev, "Unexpected write after address setup\n");
		}
        fdata->total_writes++;
		break;

	case I2C_SLAVE_READ_REQUESTED:
		/* Master starts reading */
		if (!fdata->address_set) {
			*val = 0xFF;  // Return dummy data if offset not set
			dev_warn(&client->dev, "Read without setting offset\n");
			break;
		}
		
		spin_lock(&fdata->buffer_lock);
		
		/* Check bounds */
		if (fdata->current_offset < fdata->file_size) {
			*val = fdata->file_buffer[fdata->current_offset];
		} else {
			*val = 0xFF;  // Return 0xFF for out-of-bounds read
			dev_info(&client->dev, "Read beyond file size: %u >= %u\n",
				fdata->current_offset, fdata->file_size);
		}
		
		spin_unlock(&fdata->buffer_lock);
        fdata->total_reads++;
		break;

	case I2C_SLAVE_READ_PROCESSED:
		/* Previous byte successfully sent, increment offset */
		spin_lock(&fdata->buffer_lock);
		
		if (fdata->current_offset < fdata->file_size) {
			fdata->current_offset++;
		}
		
		spin_unlock(&fdata->buffer_lock);
		
		/* Prepare next byte */
		spin_lock(&fdata->buffer_lock);
		
		if (fdata->current_offset < fdata->file_size) {
			*val = fdata->file_buffer[fdata->current_offset];
		} else {
			*val = 0xFF;
		}
		
		spin_unlock(&fdata->buffer_lock);
        fdata->total_reads++;
		break;

	case I2C_SLAVE_STOP:
		/* Reset address byte counter only */
		/* IMPORTANT: Keep address_set and current_offset for subsequent reads */
		fdata->addr_byte_count = 0;
		break;
	
	case I2C_SLAVE_WRITE_REQUESTED:
		/* New write transaction starts - reset byte counter only */
		/* address_set will be cleared when first address byte arrives */
        dev_info(&client->dev, "Exprom-i2c received WRITE_REQUESTED\n");
		fdata->addr_byte_count = 0;
		break;

	default:
		break;
	}

	return 0;
}

static ssize_t i2c_slave_file_bin_write(struct file *filp, struct kobject *kobj,
		struct bin_attribute *attr, char *buf, loff_t off, size_t count)
{
	struct file_slave_data *fdata;
	unsigned long flags;
    struct device *dev = kobj_to_dev(kobj);

	fdata = dev_get_drvdata(kobj_to_dev(kobj));

	/* Validate write operation */
	if (off + count > MAX_FILE_SIZE) {
		pr_err("Write exceeds maximum file size (48MB)\n");
		return -EFBIG;
	}

	spin_lock_irqsave(&fdata->buffer_lock, flags);
	
	/* Copy data from userspace to kernel buffer */
	memcpy(&fdata->file_buffer[off], buf, count);
	
	if (off == 0) {
		fdata->file_size = count;
	} else if (off + count > fdata->file_size) {
		fdata->file_size = off + count;
	}
	fdata->last_load_size = count;

	spin_unlock_irqrestore(&fdata->buffer_lock, flags);


	if (off == 0) {
    		printk(KERN_INFO "========================================\n");
    		printk(KERN_INFO "exprom: File loaded or overwritten!\n");
    		printk(KERN_INFO "========================================\n");
    		printk(KERN_INFO "exprom: New size: %u bytes\n", fdata->file_size);
    		printk(KERN_INFO "exprom: First 16 bytes:\n");
    		printk(KERN_INFO "exprom:   [00-07]: %02x %02x %02x %02x %02x %02x %02x %02x\n",
           		fdata->file_buffer[0], fdata->file_buffer[1],
           		fdata->file_buffer[2], fdata->file_buffer[3],
           		fdata->file_buffer[4], fdata->file_buffer[5],
           		fdata->file_buffer[6], fdata->file_buffer[7]);
    		printk(KERN_INFO "exprom:   [08-15]: %02x %02x %02x %02x %02x %02x %02x %02x\n",
           		fdata->file_buffer[8], fdata->file_buffer[9],
           		fdata->file_buffer[10], fdata->file_buffer[11],
           		fdata->file_buffer[12], fdata->file_buffer[13],
           		fdata->file_buffer[14], fdata->file_buffer[15]);
    		printk(KERN_INFO "========================================\n");

    		dev_info(dev, "File loaded/overwritten: %u bytes\n", fdata->file_size);
	} else {
    		printk(KERN_INFO "exprom: Data updated: offset=%lld, count=%zu bytes\n",
           		off, count);
    		dev_info(dev, "Data updated at offset %lld\n", off);
	}

	return count;

}

static ssize_t i2c_slave_file_bin_read(struct file *filp, struct kobject *kobj,
		struct bin_attribute *attr, char *buf, loff_t off, size_t count)
{
	struct file_slave_data *fdata;
	unsigned long flags;
	size_t read_count;

	fdata = dev_get_drvdata(kobj_to_dev(kobj));

	spin_lock_irqsave(&fdata->buffer_lock, flags);
	
	/* Limit read to actual file size */
	if (off >= fdata->file_size) {
		spin_unlock_irqrestore(&fdata->buffer_lock, flags);
		return 0;
	}
	
	read_count = min_t(size_t, count, fdata->file_size - off);
	memcpy(buf, &fdata->file_buffer[off], read_count);
	
	spin_unlock_irqrestore(&fdata->buffer_lock, flags);

	return read_count;
}

/* Sysfs attribute to show current file size */
static ssize_t file_size_show(struct device *dev,
			      struct device_attribute *attr, char *buf)
{
	struct file_slave_data *fdata = dev_get_drvdata(dev);
	
	return sprintf(buf, "%u\n", fdata->file_size);
}
static DEVICE_ATTR_RO(file_size);

/* Sysfs attribute to show/set current offset */
static ssize_t current_offset_show(struct device *dev,
				   struct device_attribute *attr, char *buf)
{
	struct file_slave_data *fdata = dev_get_drvdata(dev);
	
	return sprintf(buf, "0x%08X (%u)\n", fdata->current_offset, fdata->current_offset);
}
static DEVICE_ATTR_RO(current_offset);

/* Sysfs attribute to show statistics */
static ssize_t statistics_show(struct device *dev,
			       struct device_attribute *attr, char *buf)
{
	struct file_slave_data *fdata = dev_get_drvdata(dev);
	
	return sprintf(buf, 
		       "Total I2C Reads:  %lu\n"
		       "Total I2C Writes: %lu\n"
		       "Last Load Size:   %u bytes\n"
		       "Current Offset:   0x%08X\n"
		       "Address Set:      %s\n",
		       fdata->total_reads,
		       fdata->total_writes,
		       fdata->last_load_size,
		       fdata->current_offset,
		       fdata->address_set ? "Yes" : "No");
}
static DEVICE_ATTR_RO(statistics);

static struct attribute *i2c_slave_file_attrs[] = {
	&dev_attr_file_size.attr,
	&dev_attr_current_offset.attr,
    &dev_attr_statistics.attr,
	NULL,
};
ATTRIBUTE_GROUPS(i2c_slave_file);

static int i2c_slave_file_probe(struct i2c_client *client)
{
	struct file_slave_data *fdata;
	int ret;

    dev_info(&client->dev, "--> [EXPROM/exprom] [HieuCao i2c-slave Module Probing ver 2.0.0 ...] ");
	dev_info(&client->dev, "EXPROM probe starting, Mounting I2C @ address: 0x%02x\n", client->addr);


	/* Allocate driver data structure */
	fdata = devm_kzalloc(&client->dev, sizeof(*fdata), GFP_KERNEL);
	if (!fdata)
		return -ENOMEM;

	/* Allocate 48MB buffer using vmalloc (too large for kmalloc) */
	fdata->file_buffer = vmalloc(MAX_FILE_SIZE);
	if (!fdata->file_buffer) {
		dev_err(&client->dev, "Failed to allocate 48MB buffer\n");
		return -ENOMEM;
	}

	/* Initialize buffer with 0xFF (like empty EEPROM) */
	memset(fdata->file_buffer, 0xFF, MAX_FILE_SIZE);

	/* Initialize fields */
	spin_lock_init(&fdata->buffer_lock);
	fdata->current_offset = 0;
	fdata->file_size = 0;
	fdata->addr_byte_count = 0;
	fdata->address_set = false;
    fdata->total_reads = 0;
	fdata->total_writes = 0;
	fdata->last_load_size = 0;
	
	i2c_set_clientdata(client, fdata);

	/* Create sysfs binary attribute for file operations */
	sysfs_bin_attr_init(&fdata->bin);
	fdata->bin.attr.name = "exprom-file";
	fdata->bin.attr.mode = 0644;
	fdata->bin.read = i2c_slave_file_bin_read;
	fdata->bin.write = i2c_slave_file_bin_write;
	fdata->bin.size = MAX_FILE_SIZE;

	ret = sysfs_create_bin_file(&client->dev.kobj, &fdata->bin);
	if (ret) {
		dev_err(&client->dev, "Failed to create sysfs file\n");
		goto err_free_buffer;
	}

	/* Create sysfs attributes group */
	ret = sysfs_create_groups(&client->dev.kobj, i2c_slave_file_groups);
	if (ret) {
		dev_err(&client->dev, "Failed to create sysfs attributes\n");
		goto err_remove_bin;
	}

	/* Register as I2C slave */
	ret = i2c_slave_register(client, i2c_slave_file_slave_cb);
	if (ret) {
		dev_err(&client->dev, "Failed to register I2C slave\n");
		goto err_remove_groups;
	}

	dev_info(&client->dev, "I2C Slave EXPROM-File Reader ready (48MB max)\n");
	return 0;

err_remove_groups:
	sysfs_remove_groups(&client->dev.kobj, i2c_slave_file_groups);
err_remove_bin:
	sysfs_remove_bin_file(&client->dev.kobj, &fdata->bin);
err_free_buffer:
	vfree(fdata->file_buffer);
	return ret;
}

static void i2c_slave_file_remove(struct i2c_client *client)
{
	struct file_slave_data *fdata = i2c_get_clientdata(client);

	i2c_slave_unregister(client);
	sysfs_remove_groups(&client->dev.kobj, i2c_slave_file_groups);
	sysfs_remove_bin_file(&client->dev.kobj, &fdata->bin);
	vfree(fdata->file_buffer);
	
	dev_info(&client->dev, "I2C Slave EXPROM-File Reader removed\n");
}

static const struct i2c_device_id exprom_id[] = {
	{ "exprom", 0 },
	{ }
};
MODULE_DEVICE_TABLE(i2c, exprom_id);

static const struct of_device_id exprom_of_match[] = {
	{ .compatible = "linux,exprom" },
	{ }
};
MODULE_DEVICE_TABLE(of, exprom_of_match);

static struct i2c_driver exprom_driver = {
	.driver = {
		.name = "exprom",
		.of_match_table = exprom_of_match,
	},
	.probe_new = i2c_slave_file_probe,
	.remove = i2c_slave_file_remove,
	.id_table = exprom_id,
};
module_i2c_driver(exprom_driver);

MODULE_AUTHOR("Cao Hieu");
MODULE_DESCRIPTION("I2C slave mode 48MB exprom-file reader");
MODULE_LICENSE("GPL v2");
