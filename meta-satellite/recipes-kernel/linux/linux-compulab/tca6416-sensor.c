// tca6416-sensor.c - Driver for TCA6416 GPIO expander (Sensor Switcher)
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/i2c.h>
#include <linux/device.h>
#include <linux/sysfs.h>
#include <linux/mutex.h>
#include <linux/delay.h>

#define DRIVER_NAME "tca6416-sensor"
#define MAX_SENSORS 4

// TCA6416 Register addresses
#define OUTPUT_PORT0    0x02
#define OUTPUT_PORT1    0x03
#define CONFIG_PORT0    0x06
#define CONFIG_PORT1    0x07

struct tca6416_data {
    struct i2c_client *client;
    int current_sensor;
    struct mutex lock;
    u8 port0_state;
    u8 port1_state;
};

static int tca6416_write_reg(struct tca6416_data *data, u8 reg, u8 val)
{
    int ret;
    
    ret = i2c_smbus_write_byte_data(data->client, reg, val);
    if (ret < 0) {
        dev_err(&data->client->dev, "Failed to write reg 0x%02x: %d\n", reg, ret);
    }
    return ret;
}

static int tca6416_read_reg(struct tca6416_data *data, u8 reg, u8 *val)
{
    int ret;
    
    ret = i2c_smbus_read_byte_data(data->client, reg);
    if (ret < 0) {
        dev_err(&data->client->dev, "Failed to read reg 0x%02x: %d\n", reg, ret);
        return ret;
    }
    *val = ret;
    return 0;
}

static int tca6416_set_pin(struct tca6416_data *data, int port, int pin, int state)
{
    u8 reg = (port == 0) ? OUTPUT_PORT0 : OUTPUT_PORT1;
    u8 *current_state = (port == 0) ? &data->port0_state : &data->port1_state;
    u8 new_value;
    
    if (state)
        new_value = *current_state | (1 << pin);
    else
        new_value = *current_state & ~(1 << pin);
    
    if (tca6416_write_reg(data, reg, new_value) < 0)
        return -EIO;
    
    *current_state = new_value;
    return 0;
}

static int tca6416_initialize(struct tca6416_data *data)
{
    int ret;
    
    // Configure all pins as outputs
    ret = tca6416_write_reg(data, CONFIG_PORT0, 0x00);
    if (ret < 0)
        return ret;
    
    ret = tca6416_write_reg(data, CONFIG_PORT1, 0x00);
    if (ret < 0)
        return ret;
    
    // Initialize all outputs to 0
    ret = tca6416_write_reg(data, OUTPUT_PORT0, 0x00);
    if (ret < 0)
        return ret;
    
    ret = tca6416_write_reg(data, OUTPUT_PORT1, 0x00);
    if (ret < 0)
        return ret;
    
    data->port0_state = 0x00;
    data->port1_state = 0x00;
    
    dev_info(&data->client->dev, "TCA6416 initialized\n");
    return 0;
}

static int tca6416_enable_sensor(struct tca6416_data *data, int sensor)
{
    int ret = 0;
    
    if (sensor < 0 || sensor >= MAX_SENSORS) {
        dev_err(&data->client->dev, "Invalid sensor: %d (must be 0-%d)\n", 
                sensor, MAX_SENSORS - 1);
        return -EINVAL;
    }
    
    mutex_lock(&data->lock);
    
    // Reinitialize to clear previous state
    ret = tca6416_initialize(data);
    if (ret < 0)
        goto out;
    
    switch (sensor) {
    case 0:  // U1
        tca6416_set_pin(data, 1, 7, 0);
        tca6416_set_pin(data, 1, 6, 1);
        tca6416_set_pin(data, 1, 5, 1);
        tca6416_set_pin(data, 1, 4, 1);
        usleep_range(10000, 12000);  // 10ms delay
        tca6416_set_pin(data, 1, 0, 0);
        tca6416_set_pin(data, 1, 1, 0);
        usleep_range(10000, 12000);  // 10ms delay
        tca6416_set_pin(data, 0, 7, 1);
        tca6416_set_pin(data, 0, 6, 0);
        tca6416_set_pin(data, 0, 5, 0);
        tca6416_set_pin(data, 0, 4, 0);
        break;
        
    case 1:  // U2
        tca6416_set_pin(data, 1, 7, 1);
        tca6416_set_pin(data, 1, 6, 0);
        tca6416_set_pin(data, 1, 5, 1);
        tca6416_set_pin(data, 1, 4, 1);
        usleep_range(10000, 12000);
        tca6416_set_pin(data, 1, 0, 1);
        tca6416_set_pin(data, 1, 1, 0);
        usleep_range(10000, 12000);
        tca6416_set_pin(data, 0, 7, 0);
        tca6416_set_pin(data, 0, 6, 1);
        tca6416_set_pin(data, 0, 5, 0);
        tca6416_set_pin(data, 0, 4, 0);
        break;
        
    case 2:  // U3
        tca6416_set_pin(data, 1, 7, 1);
        tca6416_set_pin(data, 1, 6, 1);
        tca6416_set_pin(data, 1, 5, 0);
        tca6416_set_pin(data, 1, 4, 1);
        usleep_range(10000, 12000);
        tca6416_set_pin(data, 1, 0, 0);
        tca6416_set_pin(data, 1, 1, 1);
        usleep_range(10000, 12000);
        tca6416_set_pin(data, 0, 7, 0);
        tca6416_set_pin(data, 0, 6, 0);
        tca6416_set_pin(data, 0, 5, 1);
        tca6416_set_pin(data, 0, 4, 0);
        break;
        
    case 3:  // U4
        tca6416_set_pin(data, 1, 7, 1);
        tca6416_set_pin(data, 1, 6, 1);
        tca6416_set_pin(data, 1, 5, 1);
        tca6416_set_pin(data, 1, 4, 0);
        usleep_range(10000, 12000);
        tca6416_set_pin(data, 1, 0, 1);
        tca6416_set_pin(data, 1, 1, 1);
        usleep_range(10000, 12000);
        tca6416_set_pin(data, 0, 7, 0);
        tca6416_set_pin(data, 0, 6, 0);
        tca6416_set_pin(data, 0, 5, 0);
        tca6416_set_pin(data, 0, 4, 1);
        break;
    }
    
    data->current_sensor = sensor;
    dev_info(&data->client->dev, "Enabled sensor U%d\n", sensor + 1);
    
out:
    mutex_unlock(&data->lock);
    return ret;
}

// Sysfs: current_sensor (read/write)
static ssize_t current_sensor_show(struct device *dev,
                                    struct device_attribute *attr, char *buf)
{
    struct tca6416_data *data = dev_get_drvdata(dev);
    return sprintf(buf, "%d\n", data->current_sensor);
}

static ssize_t current_sensor_store(struct device *dev,
                                     struct device_attribute *attr,
                                     const char *buf, size_t count)
{
    struct tca6416_data *data = dev_get_drvdata(dev);
    int sensor, ret;
    
    ret = kstrtoint(buf, 10, &sensor);
    if (ret)
        return ret;
    
    ret = tca6416_enable_sensor(data, sensor);
    if (ret)
        return ret;
    
    return count;
}
static DEVICE_ATTR_RW(current_sensor);

// Sysfs: available_sensors (read-only)
static ssize_t available_sensors_show(struct device *dev,
                                       struct device_attribute *attr, char *buf)
{
    return sprintf(buf, "0 1 2 3\n");
}
static DEVICE_ATTR_RO(available_sensors);

static struct attribute *tca6416_attrs[] = {
    &dev_attr_current_sensor.attr,
    &dev_attr_available_sensors.attr,
    NULL,
};

static const struct attribute_group tca6416_attr_group = {
    .name = "sensor_switch",
    .attrs = tca6416_attrs,
};

static int tca6416_probe(struct i2c_client *client,
                         const struct i2c_device_id *id)
{
    struct tca6416_data *data;
    int ret;
    
    dev_info(&client->dev, "Probing TCA6416 sensor switcher\n");
    
    if (!i2c_check_functionality(client->adapter, 
                                  I2C_FUNC_SMBUS_BYTE_DATA)) {
        dev_err(&client->dev, "I2C adapter doesn't support required functionality\n");
        return -ENODEV;
    }
    
    data = devm_kzalloc(&client->dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;
    
    data->client = client;
    data->current_sensor = -1;
    mutex_init(&data->lock);
    
    i2c_set_clientdata(client, data);
    
    // Initialize TCA6416
    ret = tca6416_initialize(data);
    if (ret) {
        dev_err(&client->dev, "Failed to initialize TCA6416: %d\n", ret);
        return ret;
    }
    
    // Create sysfs attributes
    ret = sysfs_create_group(&client->dev.kobj, &tca6416_attr_group);
    if (ret) {
        dev_err(&client->dev, "Failed to create sysfs group: %d\n", ret);
        return ret;
    }
    
    // Enable sensor 0 (U1) by default
    ret = tca6416_enable_sensor(data, 0);
    if (ret) {
        dev_err(&client->dev, "Failed to enable default sensor 0: %d\n", ret);
        sysfs_remove_group(&client->dev.kobj, &tca6416_attr_group);
        return ret;
    }
    
    dev_info(&client->dev, "TCA6416 sensor switcher initialized (default: sensor 0)\n");
    return 0;
}

static void tca6416_remove(struct i2c_client *client)
{
    sysfs_remove_group(&client->dev.kobj, &tca6416_attr_group);
    dev_info(&client->dev, "TCA6416 sensor switcher removed\n");
}

static const struct i2c_device_id tca6416_id[] = {
    { "tca6416-sensor", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, tca6416_id);

static const struct of_device_id tca6416_of_match[] = {
    { .compatible = "ti,tca6416-sensor" },
    { }
};
MODULE_DEVICE_TABLE(of, tca6416_of_match);

static struct i2c_driver tca6416_driver = {
    .driver = {
        .name = DRIVER_NAME,
        .of_match_table = tca6416_of_match,
    },
    .probe = tca6416_probe,
    .remove = tca6416_remove,
    .id_table = tca6416_id,
};

module_i2c_driver(tca6416_driver);

MODULE_AUTHOR("Hieu Cao");
MODULE_DESCRIPTION("TCA6416 GPIO Expander Sensor Switcher Driver");
MODULE_LICENSE("GPL");
MODULE_VERSION("1.0");
