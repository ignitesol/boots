<?xml version="1.0" ?>
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<!-- For ipad/iphone -->
		<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, minimum-scale=1, user-scalable=0" />
		<meta name="apple-mobile-web-app-capable" content="yes" />
		<meta name="apple-mobile-web-app-status-bar-style" content="black" />
		<link rel="apple-touch-icon-precomposed" href="/images/appicon12.gif"/>
		<link href="/boots/css/admin.css" rel="stylesheet" type="text/css" />
		<link href="/boots/css/accordion.css" rel="stylesheet" type="text/css" />
        <link href="/boots/css/jquery.ui.accordion.css" rel="stylesheet" type="text/css" />
		
		<script src="/boots/lib/dojo.minified/dojo.min.js" type="text/javascript" djConfig="parseOnLoad:true"></script>
		<script src="/boots/js/ajax.js" type="text/javascript"></script>
		<script src="/boots/js/adminui.js" type="text/javascript"></script>
		<script src="/boots/js/accordion.js" type="text/javascript"></script>
		
        <script src="/boots/js/jquery-1.7.1.min.js" type="text/javascript"></script>
        <script src="/boots/js/jquery.ui.core.js" type="text/javascript"></script>
        <script src="/boots/js/jquery.ui.widget.js" type="text/javascript"></script>
        <script src="/boots/js/jquery.ui.accordion.js" type="text/javascript"></script>
		

        <title>{{name}} | SPARX Manager</title>
	</head>
	%try:
		<label>{{error}}</label>
	%except:
		<body id="manage" onload="SPARX.Manage.initialize('{{prefix}}',{{tabs}});">
          <div id="config_sections">Sections: 
			<select id="sections">
			  
			</select>
		  </div>
		  <div id="pages">
		  </div>
		  <div id="popup" style="background-color:rgba(0,0,0,0.7);position:absolute;width:100%;height:100%;z-index:1000;top:0px;display:none;">
		  </div>
		</body>
	%end
</html>
