# EXP-Satellite Kernel

## Build Image

### Setup Yocto environment

* WorkDir:
```
mkdir compulab-nxp-bsp && cd compulab-nxp-bsp
```
* Set a CompuLab machine:

```
export MACHINE=ucm-imx93
```

### Initialize repo manifests

* NXP
```
repo init -u https://github.com/nxp-imx/imx-manifest.git -b imx-linux-mickledore -m imx-6.1.55-2.2.0.xml
```

* CompuLab
```
mkdir -p .repo/local_manifests
wget --directory-prefix .repo/local_manifests https://raw.githubusercontent.com/compulab-yokneam/meta-bsp-imx9/mickledore-6.1.55-2.0/scripts/meta-bsp-imx9.xml
repo sync
```
### Setup build environment

* Initialize the build environment:
```
source compulab-setup-env -b build-${MACHINE}
```

### Add custom meta, make change `bb.conf`, `local.conf`

###  Building full rootfs image:

* Build command 
```
bitbake core-image-satellite
```

### Deploy Image:
* Recommend to use `Rufus 4.9p`:
* Flash this image:
```
build-ucm-imx93/tmp/deploy/images/ucm-imx93/core-image-satellite-ucm-imx93-.rootfs.wic.zst
```
### User Access:
```
   $> usr: root / pwd: 1234
   $> usr: bee / pwd: SLt@2025
```

## DFT
### RNDIS USB Ethernet:
* **`bee`**
``` 
sudo ifconfig usb0 192.168.6.7 netmask 255.255.255.0 up 
```
### Console:
* UART1 (A55):

<p align="center">
  <img src="docs/image.png" width="50%">
  <img src="docs/image-1.png" width="50%">
</p>

* UART2 (M33):

<p align="center">
  <img src="docs/image-2.png" width="50%">
  <img src="docs/image-3.png" width="50%">
</p>
