SPARX.Manage.Logging = function(){
	var config = {};
	var loggers = {};
	var handlers = {};
	var filters = {};
	var logging_lvl_map={
		0:"NOTSET",
		10:"DEBUG",
		20:"INFO",
		30:"WARNING/WARN",
		40:"ERROR",
		50:"CRITICAL/FATAL",
	};
	
	return {
		setup : function(name){
			SPARX.Manage.add_config_section_handler(name,SPARX.Manage.Logging.initialize);
			SPARX.Manage.add_config_section_save(name,SPARX.Manage.Logging.save);
		},
		initialize : function(name, new_config){
			config = new_config;
			SPARX.Manage.Logging.show_config();
		},
		show_config : function(){
			var config_page = document.getElementById("logging_page");
			loggers = config.loggers || [];
			SPARX.Manage.Logging.load_loggers();
			handlers = config.handlers || [];
			SPARX.Manage.Logging.load_handlers();
			filters = config.filters || [];
			SPARX.Manage.Logging.load_filters();
		},
		load_loggers : function(){
			SPARX.Manage.Logging.load("loggers", loggers, 'SPARX.Manage.Logging.logger_selected');
		},
		load_handlers : function(){
			SPARX.Manage.Logging.load("handlers", handlers, 'SPARX.Manage.Logging.handler_selected');
		},
		load_filters : function(){
			SPARX.Manage.Logging.load("filters", filters, 'SPARX.Manage.Logging.filter_selected');
		},
		load : function(name , data, func){
			var handler_ele = document.getElementById(name)
			handler_ele.innerHTML = "";
			for(var name in data){
				if(data[name].level != undefined)
					data[name].level = logging_lvl_map[(data[name].level || 0)];
				handler_ele.innerHTML = handler_ele.innerHTML + "<option value='1' onclick='"+func+"(event)'>"+name+"</option>"; 
			}
		},
		logger_selected : function(event){
			//console.log(event.currentTarget.innerText);
			var logger_name = event.currentTarget.innerText;
			var logger_properties = loggers[logger_name];
			var curr_logger_handlers = logger_properties.handlers || [];
			var curr_logger_filters = logger_properties.filters || [];
			var curr_logger_level = logger_properties.level || 0;
			var curr_logger_available_filters = filters;
			var curr_logger_available_handlers = handlers;
			if(logger_properties){
				var logger_properties_html = "<center><h2>Logger Configuration</h2></center></br><table style='margin:10px;'>";
				logger_properties_html = logger_properties_html + "<tr><td>Name</td><td>" + logger_name + "</td></tr>";
				logger_properties_html = logger_properties_html + "<tr><td><input type='checkbox' name='logger_disabled' value='disabled'";
				if(logger_properties.disabled == 1)
					logger_properties_html = logger_properties_html +  "checked";
				logger_properties_html = logger_properties_html + "></td><td><label>Disabled</label></td></tr>";
				logger_properties_html = logger_properties_html + "<tr><td><input type='checkbox' name='logger_propagate' value='propagate'";
				if(logger_properties.propagate == 1)
					logger_properties_html = logger_properties_html +  "checked";
				logger_properties_html = logger_properties_html + "></td><td><label>Propagate</label></td></tr>"
				logger_properties_html = logger_properties_html + "<tr><td><label>Handlers</label></td><td><select name='Logger Handlers' id='logger_"+logger_name+"_handlers' size='5' style='width:100%;'>";
				for(var i in curr_logger_handlers){
					var temp = {};
					for(var j in curr_logger_available_handlers){
						if(j != curr_logger_handlers[i])
							temp[j] = curr_logger_available_handlers[j];
					}
					curr_logger_available_handlers = temp;
					logger_properties_html = logger_properties_html + "<option value='"+curr_logger_handlers[i]+"'>"+curr_logger_handlers[i]+"</option>";
				}
				logger_properties_html = logger_properties_html + "</select></td><td><div style='width:32px;'><img src='/fabric/images/back.png'  onclick='SPARX.Manage.Logging.new_data(SPARX.Manage.UI.selector_move(\"logger_"+logger_name+"_handlers\",\"available_handlers\"));'/><img src='/fabric/images/next.png' onclick='SPARX.Manage.Logging.new_data(SPARX.Manage.UI.selector_move(\"available_handlers\",\"logger_"+logger_name+"_handlers\"));'/></div></td>";
				logger_properties_html = logger_properties_html + "<td><select name='Available Handlers' id='available_handlers' size='5' style='width:100%;'>";
				for(var handler_name in curr_logger_available_handlers){
					logger_properties_html = logger_properties_html + "<option value='" + handler_name + "'>" + handler_name + "</option>";
				}
				logger_properties_html = logger_properties_html + "</select></td></tr>";
				logger_properties_html = logger_properties_html + "<tr><td><label>Filters</label></td><td><select name='Logger Filters' id='logger_"+logger_name+"_filters' size='5' style='width:100%;'>";
				for(var i in curr_logger_filters){
					var temp = {};
					for(var j in curr_logger_available_filters){
						if(j != curr_logger_filters[i])
							temp[j] = curr_logger_available_filters[j];
					}
					curr_logger_available_filters = temp;
					logger_properties_html = logger_properties_html + "<option value='"+curr_logger_filters[i]+"'>"+curr_logger_filters[i]+"</option>";
				}
				logger_properties_html = logger_properties_html + "</select></td><td><div style='width:32px;'><img src='/fabric/images/back.png'  onclick='SPARX.Manage.Logging.new_data(SPARX.Manage.UI.selector_move(\"logger_"+logger_name+"_filters\",\"available_filters\"));'/><img src='/fabric/images/next.png' onclick='SPARX.Manage.Logging.new_data(SPARX.Manage.UI.selector_move(\"available_filters\",\"logger_"+logger_name+"_filters\"));'/></div></td>";
				logger_properties_html = logger_properties_html + "<td><select name='Available Handlers' id='available_filters' size='5' style='width:100%;'>";
				for(var filter_name in curr_logger_available_filters){
					logger_properties_html = logger_properties_html + "<option value='" + filter_name + "'>" + filter_name + "</option>";
				}
				logger_properties_html = logger_properties_html + "</select></td></tr>";
				logger_properties_html = logger_properties_html + "<tr><td><label>Level</label></td><td><select name='Logger Level' id='logger_level' size='6'>";
				for(var lvl=0;lvl<=50;lvl=lvl+10)
				{
					logger_properties_html = logger_properties_html + "<option value='"+lvl+"' onclick='SPARX.Manage.Logging.new_data_for_loggers(\""+logger_name+"\",\"level\",\""+logging_lvl_map[lvl]+"\")'";
					if(curr_logger_level == logging_lvl_map[lvl])
						logger_properties_html = logger_properties_html + " selected";		
					logger_properties_html = logger_properties_html + ">" + logging_lvl_map[lvl] + "</option>";
				}
				logger_properties_html = logger_properties_html + "</select></td></tr>";
				logger_properties_html = logger_properties_html + "</table>";
				SPARX.Manage.Logging.set_and_show(logger_properties_html);
			}
			else
				SPARX.Manage.Logging.set_and_show("No Logger Info Available");
		},
		handler_selected : function(event){
			//console.log(event.currentTarget.innerText);
			var handler_name = event.currentTarget.innerText
			var handler_properties = handlers[handler_name];
			var curr_handler_filters = handler_properties.filters || [];
			var curr_handler_level = handler_properties.level || 0;
			var curr_handler_available_filters = filters;
			if(handler_properties){
				var handler_properties_html = "<center><h2>Handler Configuration</h2></center></br><table style='margin:10px;'>";
				handler_properties_html = handler_properties_html + "<tr><td>Name</td><td>" + handler_name + "</td></tr>";
				handler_properties_html = handler_properties_html + "<tr><td><label>Class</label></td><td>" + handler_properties.class + "</td></tr>";
				handler_properties_html = handler_properties_html + "<tr><td><label>Formatter</label></td><td>" + handler_properties.formatter || "NA" + "</td></tr>"
				handler_properties_html = handler_properties_html + "<tr><td><label>Stream</label></td><td>" + (handler_properties.stream || "NA") + "</td></tr><tr>";
				handler_properties_html = handler_properties_html + "<tr><td><label>Filename</label></td><td>" + (handler_properties.filename || "NA") + "</td></tr><tr>";
				handler_properties_html = handler_properties_html + "<tr><td><label>BackupCount</label></td><td>" + (handler_properties.backupCount || "NA") + "</td></tr><tr>";
				handler_properties_html = handler_properties_html + "<tr><td><label>Max Bytes</label></td><td>" + (handler_properties.maxBytes || "NA") + "</td></tr>";
				handler_properties_html = handler_properties_html + "<tr><td><label>Filters</label></td><td><select name='Handler Filters' id='handler_"+handler_name+"_filter' size='5' style='width:100%;'>";
				for(var i in curr_handler_filters){
					var temp = {};
					for(var j in curr_handler_available_filters){
						if(j != curr_handler_filters[i])
							temp[j] = curr_handler_available_filters[j];
					}
					curr_handler_available_filters = temp;
					handler_properties_html = handler_properties_html + "<option value='"+curr_handler_filters[i]+"'>"+curr_handler_filters[i]+"</option>";
				}
				handler_properties_html = handler_properties_html + "</select></td><td><div style='width:32px;'><img src='/fabric/images/back.png'  onclick='SPARX.Manage.Logging.new_data(SPARX.Manage.UI.selector_move(\"handler_"+handler_name+"_filter\",\"available_filters\"));'/><img src='/fabric/images/next.png' onclick='SPARX.Manage.Logging.new_data(SPARX.Manage.UI.selector_move(\"available_filters\",\"handler_"+handler_name+"_filter\"));'/></div></td>";
				handler_properties_html = handler_properties_html + "<td><select name='Available Filters' id='available_filters' size='5' style='width:100%;'>";
				for(var filter_name in curr_handler_available_filters){
					handler_properties_html = handler_properties_html + "<option value='" + filter_name + "'>" + filter_name + "</option>";
				}
				handler_properties_html = handler_properties_html + "</select></td></tr>";
				handler_properties_html = handler_properties_html + "<tr><td><label>Level</label></td><td><select name='Handler Level' id='handler_level' size='6'>";
				for(var lvl=0;lvl<=50;lvl=lvl+10)
				{
					handler_properties_html = handler_properties_html + "<option value='"+lvl+"' onclick='SPARX.Manage.Logging.new_data_for_handlers(\""+handler_name+"\",\"level\",\""+logging_lvl_map[lvl]+"\")'";
					if(curr_handler_level == logging_lvl_map[lvl])
						handler_properties_html = handler_properties_html + " selected";		
					handler_properties_html = handler_properties_html + ">" + logging_lvl_map[lvl] + "</option>";
				}
				handler_properties_html = handler_properties_html + "</select></td></tr>"
				handler_properties_html = handler_properties_html + "</table>"
				SPARX.Manage.Logging.set_and_show(handler_properties_html);	
			}
			else
				SPARX.Manage.Logging.set_and_show("No Handler Info Available");
		},
		set_and_show : function(HTML){
			document.getElementById("popup_content").innerHTML = HTML;	
			document.getElementById("popup").style.display = "block";
			document.getElementById("popup_page").style.display = "block";
			document.getElementById('add_filter_div').style.display='none';
			document.getElementById('add_filter_button').style.display='block';
		},
		filter_selected : function(event){
			//console.log(event.currentTarget.innerText);
			var filter_name = event.currentTarget.innerText;
			var filter_properties = filters[filter_name];
			var curr_filter_level = filter_properties.level || 0;
			if(filter_properties){
				var filter_properties_html = "<center><h2>Filter Configuration</h2></center></br><table style='margin:10px;'>";
				filter_properties_html = filter_properties_html + "<tr><td>ID</td><td>" + (filter_name || "Unknown" ) + "</td></tr>";
				filter_properties_html = filter_properties_html + "<tr><td>Name</td><td>" + (filter_properties.name || "NA") + "</td></tr>";
				filter_properties_html = filter_properties_html + "<tr><td><label>Match Expression</label></td><td><input onkeypress='if(event.keyIdentifier == \"Enter\"){SPARX.Manage.Logging.new_data_for_filters(\""+filter_name+"\", \"match\",event.currentTarget.value);}' value='" + (filter_properties.match || "") + "'></input></td></tr>";
				filter_properties_html = filter_properties_html + "<tr><td><label>args</label></td>"
				filter_properties_html = filter_properties_html + "<td><select name='Args' id='filter_"+filter_name+"_args' size='5' style='width:100%;'>";
				for(var arg in filter_properties.args){
					filter_properties_html = filter_properties_html + "<option value='" + arg + "'>" + arg + "</option>";
				}
				filter_properties_html = filter_properties_html + "</select></td><td><input id='add_args_input' type='text' onkeypress='if(event.keyIdentifier == \"Enter\"){SPARX.Manage.Logging.new_data(SPARX.Manage.UI.add_to(\"filter_"+filter_name+"_args\", this));}'></input></td></tr>";
				filter_properties_html = filter_properties_html + "<tr><td><label>Level</label></td><td><select name='Filter Level' id='filter_level' size='6'>";
				for(var lvl=0;lvl<=50;lvl=lvl+10)
				{
					filter_properties_html = filter_properties_html + "<option value='"+lvl+"' onclick='SPARX.Manage.Logging.new_data_for_filters(\""+filter_name+"\",\"level\",\""+logging_lvl_map[lvl]+"\")'";
					if(curr_filter_level == logging_lvl_map[lvl])
						filter_properties_html = filter_properties_html + " selected";		
					filter_properties_html = filter_properties_html + ">" + logging_lvl_map[lvl] + "</option>";
				}
				filter_properties_html = filter_properties_html + "</select></td></tr>"
				filter_properties_html = filter_properties_html + "<tr><td><label>Line Number</label></td><td><input value='" + (filter_properties.lineno || "") + "'></input></td></tr><tr>";
				filter_properties_html = filter_properties_html + "<tr><td><label>Function Name</label></td><td><input value='" + (filter_properties.funcName || "") + "'></input></td></tr><tr>";
				filter_properties_html = filter_properties_html + "</table>"
				SPARX.Manage.Logging.set_and_show(filter_properties_html);
			}
			else
				SPARX.Manage.Logging.set_and_show("No Filter Info Available");
		},
		add_filter : function(name, match, args, level, lineno, funcname){
			filters[name] = {};
			SPARX.Manage.Logging.update_filter(name, name, match, args, level, lineno, funcname);
		},
		update_filter : function(id, name, match, args, level, lineno, funcname){
			filters[id]["()"] = "fabric_logging.FabricFilter";
			filters[id]["name"] = name;
			filters[id]["match"] = match;
			filters[id]["args"] = args;
			filters[id]["level"] = level;
			filters[id]["lineno"] = lineno;
			filters[id]["funcName"] = funcname;
		},
		new_data : function(new_data){
			var data_for = new_data.to;
			var data = new_data.data;
			var remove_data_from = new_data.from;
			
			if(data_for.search("available") < 0){
				var f = data_for.indexOf("_");
				var l = data_for.lastIndexOf("_");
				data_for = [data_for.substr(0,f),data_for.substr(f+1,l-f-1),data_for.substr(l+1)];
				if(data_for[0] == "logger"){
					SPARX.Manage.Logging.new_data_for_loggers(data_for[1], data_for[2], data);
				}
				if(data_for[0] == "handler"){
					SPARX.Manage.Logging.new_data_for_handlers(data_for[1], data_for[2], data);
				}
				if(data_for[0] == "filter"){
					SPARX.Manage.Logging.new_data_for_filters(data_for[1], data_for[2], data);
				}
			}
			if(remove_data_from.search("available") < 0){
				var f = remove_data_from.indexOf("_");
				var l = remove_data_from.lastIndexOf("_");
				remove_data_from = [remove_data_from.substr(0,f),remove_data_from.substr(f+1,l-f-1),remove_data_from.substr(l+1)];
				if(remove_data_from[0] == "logger"){
					SPARX.Manage.Logging.remove_data_from_loggers(remove_data_from[1], remove_data_from[2], data);
				}
				if(remove_data_from[0] == "handler"){
					SPARX.Manage.Logging.new_data_for_handlers(remove_data_from[1], remove_data_from[2], data);
				}
				if(remove_data_from[0] == "filter"){
					SPARX.Manage.Logging.new_data_for_filters(remove_data_from[1], remove_data_from[2], data);
				}
			}
		},
		new_data_for_loggers : function(logger_name, subcategory, data){
			if(subcategory == "disabled")
				loggers[logger_name].disabled = data;
			if(subcategory == "propagate")
				loggers[logger_name].propagate = data;
			if(subcategory == "handlers"){
				var curr_logger_handlers = loggers[logger_name].handlers || [];
				curr_logger_handlers.push(data);
				loggers[logger_name].handlers = curr_logger_handlers;
			}
			if(subcategory == "filters"){
				var curr_logger_filters = loggers[logger_name].filters || [];
				curr_logger_filters.push(data);
				loggers[logger_name].filters = curr_logger_filters;
			}
			if(subcategory == "level")
				loggers[logger_name].level = data;
		},
		new_data_for_handlers : function(handler_name, subcategory, data){
			if(subcategory == "class")
				handlers[handler_name].class = data;
			if(subcategory == "formatter")
				handlers[handler_name].formatter = data;
			if(subcategory == "stream")
				handlers[handler_name].stream = data;
			if(subcategory == "filename")
				handlers[handler_name].filename = data;
			if(subcategory == "backupCount")
				handlers[handler_name].backupCount = data;
			if(subcategory == "filter"){
				var curr_handler_filters = handlers[handler_name].filters || [];
				curr_handler_filters.push(data);
				handlers[handler_name].filters = curr_handler_filters;
			}
			if(subcategory == "level")
				handlers[handler_name].level = data;
		},
		new_data_for_filters : function(filter_name, subcategory, data){
			if(subcategory == "name")
				filters[filter_name].name = data;
			if(subcategory == "match")
				filters[filter_name].match = data;
			if(subcategory == "args"){
				var curr_filter_args = filters[filter_name].args || [];
				curr_filter_args.push(data);
				filters[filter_name].args = curr_filter_args;
			}
			if(subcategory == "level")
				filters[filter_name].level = data;
			if(subcategory == "lineno")
				filters[filter_name].lineno = data;
			if(subcategory == "funcName")
				filters[filter_name].funcName = data;
		},
		remove_data_from_loggers : function(logger_name, subcategory, data){
			if(subcategory == "handlers"){
				var curr_logger_handlers = [];
				for(var i in loggers[logger_name].handlers)
					if(loggers[logger_name].handlers[i] != data)
						curr_logger_handlers.push(loggers[logger_name].handlers[i]);
				loggers[logger_name].handlers = curr_logger_handlers;
			}
			if(subcategory == "filters"){
				var curr_logger_filters = [];
				for(var i in loggers[logger_name].filters)
					if(loggers[logger_name].filters[i] != data)
						curr_logger_filters.push(loggers[logger_name].filters[i]);
				loggers[logger_name].filters = curr_logger_filters;
			}
		},
		remove_data_from_handlers : function(handler_name, subcategory, data){
			if(subcategory == "filter"){
				var curr_handler_filters = [];
				for(var i in handlers[handler_name].filters)
					if(handlers[handler_name].filters[i] != data)
						curr_handler_filters.push(handlers[handler_name].filters[i]);
				handlers[handler_name].filters = curr_handler_filters;
			}
		},
		remove_data_from_handlers : function(handler_name, subcategory, data){
			if(subcategory == "args"){
				var curr_filter_args = [];
				for(var i in filters[filter_name].args)
					if(filters[filter_name].args[i] != data)
						curr_filter_args.push(filters[filter_name].args[i]);
				filters[filter_name].args = curr_filter_args;
			}
		},
		save : function(name){
			config.loggers = loggers;
			config.filters = filters;
			config.handlers = handlers;
			new_config = {};
			new_config[name] = config;
			console.log("Saving:"+new_config);
			request(SPARX.Manage.get_prefix()+"/admin/updateconfig", SPARX.Manage.Logging.onsuccess, SPARX.Manage.Logging.onerror, {configuration:JSON.stringify(new_config)}, "json")
		},
		onsuccess : function(response){
			window.alert(response.status);
		},
		onerror : function(error, args){
			window.alert(error);
		}
	}
}();

document.getElementById("Logging_reset").click();