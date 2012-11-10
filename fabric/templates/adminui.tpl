<?xml version="1.0" ?>
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<!-- For ipad/iphone -->
		<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, minimum-scale=1, user-scalable=0" />
		<meta name="apple-mobile-web-app-capable" content="yes" />
		<meta name="apple-mobile-web-app-status-bar-style" content="black" />
		<link rel="apple-touch-icon-precomposed" href="/images/appicon12.gif"/>
		<link href="/fabric/css/admin.css" rel="stylesheet" type="text/css" />
		<script src="/fabric/lib/dojo.minified/dojo.min.js" type="text/javascript" djConfig="parseOnLoad:true"></script>
		<script src="/fabric/js/ajax.js" type="text/javascript"></script>
		<script src="/fabric/js/adminui.js" type="text/javascript"></script>
		<title>{{name}} | SPARX Manager</title>
	</head>
	%try:
		<label>{{error}}</label>
	%except:
		<body id="manage" onload="SPARX.Manage.initialize('{{prefix}}',{{tabs}});">
			<div id="tabs" style="height:30px;width:100%;">
			</div>
			<div id="pages" style="position:absolute;top:30px;bottom:0px;right:0px;left:0px;border-color: #990000;border-style: solid;border-width: 0px thin;padding:0px 1px;">
			</div>
			<div id="popup" style="background-color:rgba(0,0,0,0.7);position:absolute;width:100%;height:100%;z-index:1000;top:0px;display:none;">
			</div>
		</body>
	%end
</html>