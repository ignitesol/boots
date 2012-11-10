%try:
	<label>{{error}}</label>
%except:
	<img id="{{section}}_reset" src="/fabric/images/reset.png" onclick='SPARX.Manage.add_script("loggingui.js");SPARX.Manage.{{section}}.setup("{{section}}");SPARX.Manage.run_handler("{{section}}",{{config}});' style="position:absolute;top:10px;right:10px;" />
	<div id="top_portion" style="width:100%;height:50%;">
		<div id="top_right_portion" style="width:50%;height:100%;float:right;">
			<center><h2>Filters</h2></center>
			<select name="Filters" id="filters" size="10" style="margin:5% 0px 10% 25%;width:50%;height:60%;">
			</select>
		</div>
	</div>
	<div id="bottom_portion" style="width:100%;height:50%;">
		<div id="bottom_left_portion" style="width:50%;height:100%;float:left;">
			<center><h2>Loggers</h2></center>
			<select name="Loggers" id="loggers" size="10" style="margin:5% 0px 10% 25%;width:50%;height:60%;">
			</select>
		</div>
		<div id="bottom_right_portion" style="width:50%;height:100%;float:right;">
			<center><h2>Handlers</h2></center>
			<select name="Handlers" id="handlers" size="10" style="margin:5% 0px 10% 25%;width:50%;height:60%;">
			</select>
		</div>
	</div>
	<div id="popup_page" style="position:fixed;width:50%;height:70%;top:15%;left:25%;z-index:1001;background-color: rgba(255, 255, 255, 0.5);border-radius: 10px;padding: 1%;display:none;">
		<img src="/fabric/images/close.png" style="right: 0px;position: absolute;margin: -50px;cursor:pointer;" onclick="SPARX.Manage.UI.hide('popup_page')"/>
		<div id="popup_content" style="float:left;width:50%;height:100%;background-color:white;border-radius: 8px;border-bottom-right-radius: 0px;border-top-right-radius: 0px;overflow:auto;">
		</div>
		<div id="filters" style="float:right;width:50%;height:100%;background-color:white;border-radius: 8px;border-bottom-left-radius: 0px;border-top-left-radius: 0px;">
			<button id="add_filter_button" onclick="document.getElementById('add_filter_div').style.display='block';this.style.display='none';" style="margin:10px;float:right;">Add Filter</button>
			<div id="add_filter_div" style="display:none;width:100%">
				<button onclick="document.getElementById('add_filter_div').style.display='none';document.getElementById('add_filter_button').style.display='block';" style="margin:10px;float:right;">Done</button>
				<table style="width:100%">
					<tr>
						<td>
							<label>Name</label>
						</td>
						<td>
							<input type="text" style="width:100%"></input>
						</td>
					</tr>
					<tr>
						<td>
							<label>Match Expression</label>
						</td>
						<td>
							<input type="text" style="width:100%"></input>
						</td>
					</tr>
					<tr>
						<td>
							<label>args</label>
						</td>
						<td>
							<input type="text" style="width:100%"></input>
						</td>
					</tr>
					<tr>
						<td>
							<label>Level</label>
						</td>
						<td>
							<input type="text" style="width:100%"></input>
						</td>
					</tr>
					<tr>
						<td>
							<label>Line Number</label>
						</td>
						<td>
							<input type="text" style="width:100%"></input>
						</td>
					</tr>
					<tr>
						<td>
							<label>Function Name</label>
						</td>
						<td>
							<input type="text" style="width:100%"></input>
						</td>
					</tr>
				</table>
			</div>
		</div>
	</div>
	<button id="{{section}}_button" onclick='SPARX.Manage.run_save("{{section}}");' style="position:absolute;bottom:10px;right:10px;">Save</button>
%end