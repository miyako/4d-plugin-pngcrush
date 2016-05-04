# 4d-plugin-pngcrush
Reduce size of PNG.

Based on [pngcrush 1.8.1](http://pmt.sourceforge.net/pngcrush/).

##Platform

| carbon | cocoa | win32 | win64 |
|:------:|:-----:|:---------:|:---------:|
|🆗|🆗|🆗|🆗|

##Commands

```c
// --- Pngcrush
Pngcrush
```

##Examples

```
$path:=Get 4D folder(Current resources folder)+"sample.png"
READ PICTURE FILE($path;$image;*)
$crushed:=Pngcrush ($image)
WRITE PICTURE FILE(System folder(Desktop)+"test.png";$crushed)
```

##Advanced

Pass a combination of the following flags to remove chunks.

```
PNG_REMOVE_PLTE 1
PNG_REMOVE_BKGD	2
PNG_REMOVE_CHRM 4
PNG_REMOVE_DSIG 8
PNG_REMOVE_GAMA 16
PNG_REMOVE_GIFG 32
PNG_REMOVE_GIFT 64
PNG_REMOVE_GIFX 128
PNG_REMOVE_HIST 256
PNG_REMOVE_ICCP 512
PNG_REMOVE_ITXT 1024
PNG_REMOVE_OFFS 2048
PNG_REMOVE_PHYS 4096
PNG_REMOVE_PCAL 8192
PNG_REMOVE_SBIT 16384
PNG_REMOVE_SCAL 32768
PNG_REMOVE_SRGB 65536
PNG_REMOVE_STER 131072
PNG_REMOVE_SPLT 262144
PNG_REMOVE_TEXT 524288
PNG_REMOVE_TIME 1048576
PNG_REMOVE_TRNS 2097152
PNG_REMOVE_ZTXT 4194304
```
