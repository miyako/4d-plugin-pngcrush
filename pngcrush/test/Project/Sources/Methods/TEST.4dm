//%attributes = {}
$path:=Get 4D folder:C485(Current resources folder:K5:16)+"sample.png"

READ PICTURE FILE:C678($path;$PNG)

ALERT:C41("before: "+String:C10(Picture size:C356($PNG)))

$PNG:=Pngcrush ($PNG)

ALERT:C41("after: "+String:C10(Picture size:C356($PNG)))
