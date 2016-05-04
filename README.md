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
