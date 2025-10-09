// pca9544-switch.c - Driver for PCA9544APW I2C multiplexer (Lane Switcher)
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/i2c.h>
#include <linux/device.h>
#include <linux/sysfs.h>
#include <linux/mutex.h>
#include <linux/delay.h>

#define DRIVER_NAME "pca9544-switch"
#define MAX_CHANNELS 4

// Channel control bytes for PCA9544APW
static const u8 channel_values[MAX_CHANNELS] = {
    0x04,  // Channel 0
    0x05,  // Channel 1
    0x06,  // Channel 2
    0x07   // Channel 3
};

struct pca9544_data {
    struct i2c_client *client;
    int current_channel;
    struct mutex lock;
};

static int pca9544_switch_channel(struct pca9544_data *data, int channel)
{
    int ret;
    
    if (channel < 0 || channel >= MAX_CHANNELS) {
        dev_err(&data->client->dev, "Invalid channel: %d (must be 0-%d)\n", 
                channel, MAX_CHANNELS - 1);
        return -EINVAL;
    }
    
    mutex_lock(&data->lock);
    
    // Send channel select command
    ret = i2c_smbus_write_byte(data->client, channel_values[channel]);
    if (ret < 0) {
        dev_err(&data->client->dev, "Failed to switch to channel %d: %d\n", 
                channel, ret);
        goto out;
    }
    
    // Small delay for stabilization
    usleep_range(1000, 2000);
    
    data->current_channel = channel;
    dev_info(&data->client->dev, "Switched to lane %d\n", channel);
    
out:
    mutex_unlock(&data->lock);
    return ret;
}

// Sysfs: current_lane (read/write)
static ssize_t current_lane_show(struct device *dev,
                                  struct device_attribute *attr, char *buf)
{
    struct pca9544_data *data = dev_get_drvdata(dev);
    return sprintf(buf, "%d\n", data->current_channel);
}

static ssize_t current_lane_store(struct device *dev,
                                   struct device_attribute *attr,
                                   const char *buf, size_t count)
{
    struct pca9544_data *data = dev_get_drvdata(dev);
    int channel, ret;
    
    ret = kstrtoint(buf, 10, &channel);
    if (ret)
        return ret;
    
    ret = pca9544_switch_channel(data, channel);
    if (ret)
        return ret;
    
    return count;
}
static DEVICE_ATTR_RW(current_lane);

// Sysfs: available_lanes (read-only)
static ssize_t available_lanes_show(struct device *dev,
                                     struct device_attribute *attr, char *buf)
{
    return sprintf(buf, "0 1 2 3\n");
}
static DEVICE_ATTR_RO(available_lanes);

static struct attribute *pca9544_attrs[] = {
    &dev_attr_current_lane.attr,
    &dev_attr_available_lanes.attr,
    NULL,
};

static const struct attribute_group pca9544_attr_group = {
    .name = "lane_switch",
    .attrs = pca9544_attrs,
};

static int pca9544_probe(struct i2c_client *client,
                         const struct i2c_device_id *id)
{
    struct pca9544_data *data;
    int ret;
    
    dev_info(&client->dev, "Probing PCA9544 lane switcher\n");
    
    if (!i2c_check_functionality(client->adapter, I2C_FUNC_SMBUS_WRITE_BYTE)) {
        dev_err(&client->dev, "I2C adapter doesn't support required functionality\n");
        return -ENODEV;
    }
    
    data = devm_kzalloc(&client->dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;
    
    data->client = client;
    data->current_channel = -1;
    mutex_init(&data->lock);
    
    i2c_set_clientdata(client, data);
    
    // Create sysfs attributes
    ret = sysfs_create_group(&client->dev.kobj, &pca9544_attr_group);
    if (ret) {
        dev_err(&client->dev, "Failed to create sysfs group: %d\n", ret);
        return ret;
    }
    
    // Initialize to channel 0 (default lane)
    ret = pca9544_switch_channel(data, 0);
    if (ret) {
        dev_err(&client->dev, "Failed to initialize to channel 0: %d\n", ret);
        sysfs_remove_group(&client->dev.kobj, &pca9544_attr_group);
        return ret;
    }
    
    dev_info(&client->dev, "PCA9544 lane switcher initialized (default: lane 0)\n");
    return 0;
}

static void pca9544_remove(struct i2c_client *client)
{
    sysfs_remove_group(&client->dev.kobj, &pca9544_attr_group);
    dev_info(&client->dev, "PCA9544 lane switcher removed\n");
}

static const struct i2c_device_id pca9544_id[] = {
    { "pca9544-switch", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, pca9544_id);

static const struct of_device_id pca9544_of_match[] = {
    { .compatible = "nxp,pca9544-switch" },
    { }
};
MODULE_DEVICE_TABLE(of, pca9544_of_match);

static struct i2c_driver pca9544_driver = {
    .driver = {
        .name = DRIVER_NAME,
        .of_match_table = pca9544_of_match,
    },
    .probe = pca9544_probe,
    .remove = pca9544_remove,
    .id_table = pca9544_id,
};

module_i2c_driver(pca9544_driver);

MODULE_AUTHOR("Hieu Cao");
MODULE_DESCRIPTION("PCA9544APW I2C Lane Switcher Driver");
MODULE_LICENSE("GPL");
MODULE_VERSION("1.0");
