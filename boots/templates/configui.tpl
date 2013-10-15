%try:
	<label>{{error}}</label>
%except:
	<img id="{{section}}_reset" src="/boots/images/reset.png" onclick='SPARX.Manage.run_handler("{{section}}",{{config}});' style="position:absolute;top:10px;right:10px;" />
	<div id="{{section}}_content" style="width:100%;height:100%;padding: 1%;">
		
	</div>
	<button id="{{section}}_button" onclick='SPARX.Manage.run_save("{{section}}");' style="position:absolute;bottom:10px;right:10px;">Save</button>
%end
