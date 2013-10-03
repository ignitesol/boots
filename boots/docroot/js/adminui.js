/*global SPARX, request*/

SPARX = {};

String.prototype.toTitleCase = function(){
    return this.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
};

SPARX.Manage = function(){
	var _config = {};
    var prefix = "";
	var handlers = {};
	var save = {};
	var scripts_added = [];
	return {
		/*
		 * Add javascript to the DOM, optionally it accepts the
		 * callbacks to be executed once the script is loaded
		 */
		add_script: function(script_name, callbacks) {
            function excecuteCallbacks(callbacks) {
				if(!callbacks) {
					return;
				}

                if(callbacks instanceof Array) {
                    callbacks.forEach(function(callback) {
                        callback();
                    });
                }
                else {
                    callbacks();
                }
            }

			// If the script is already added just execute the callbacks
			// and return
            if(scripts_added.indexOf(script_name) !== -1) {
                excecuteCallbacks(callbacks);
                return;
            }

			// Else create a script tag and append to the head of the document
			var script = document.createElement("script");
			script.src = '/boots/js/'+script_name;
			
			script.onload = function() {
				excecuteCallbacks(callbacks);
			};
			
			document.head.appendChild(script);
			scripts_added.push(script_name);
		},

		/*
		 * Change the section currently displayed
		 */
        change_section : function(event) {
            var section = event.srcElement.value;
			SPARX.Manage.UI.show_page(section);
        },

		/*
		 * Initialize the UI
		 */		
		initialize : function(new_prefix, list){
			prefix = new_prefix;

			/* Add the listener responsible for changing section*/
            document.getElementById("sections").onchange = SPARX.Manage.change_section;

			/* For each section add corresponding option in dropdown list
			 * Also fetch the data related to the section
			 */
			var i = -1, len = list.length;

            for(; ++i < len;){
                var new_section = list[i];

				SPARX.Manage.add_config_section_handler(new_section);
                SPARX.Manage.add_config_section_save(new_section);

                SPARX.Manage.UI.add_section(new_section);
				SPARX.Manage.get_config(new_section);
            }

			/* Finally display the default page*/
			SPARX.Manage.UI.show_page(list[0]);
		},
		add_config_section_handler : function(name, func){
            handlers[name] = func || SPARX.Manage.default_handler;
		},
		add_config_section_save : function(name, func){
			save[name] = func || SPARX.Manage.default_save;
		},

		get_config : function(name){
			request(prefix+'/admin/config/'+name,
				function(response) {
					var curr_page_ele = document.getElementById(name+"_page");
					curr_page_ele.innerHTML = response;
					var curr_page_reset_ele = document.getElementById(name+"_reset");
					curr_page_reset_ele.click();
				},function() {});
		},
		
		default_handler : function(name, config){
			document.getElementById(name+"_content").innerHTML = syntaxHighlight(name, config);
		},
		
		run_handler : function(name, config){
			_config[name] = config;
			handlers[name](name, config);
		},
		
		run_save : function(name){
			new_config = save[name](name);
//			config[page] = new_config;
		},
		get_prefix : function(){
			return prefix;
		},
		new_data : function(section, keys, new_data){
			keys = keys.split(",");
			config_section = _config[section];
			for(var i=0;i<keys.length-1;i++){
				config_section = config_section[keys[i]];
			}
			config_section[keys[keys.length-1]] = new_data;
			console.log("New data in for ",keys[keys.length-1], " is ", config_section[keys[keys.length-1]]);
		},
		default_save : function(name){
			new_config = {};
			new_config[name] = _config[name];
			console.log("Saving:"+new_config);
			request(SPARX.Manage.get_prefix()+"/admin/updateconfig", SPARX.Manage.onsuccess, SPARX.Manage.onerror, {configuration:JSON.stringify(new_config)}, "json")
		},
		onsuccess : function(response){
			window.alert(response.status);
		},
		onerror : function(error, args){
			window.alert(error);
		}
	};
}();

SPARX.Manage.UI = function(){
	var current_active_tab = null;
	var current_active_page = null;

	return{
		initialize : function(){

		},
		add_section : function(new_tab){
            function get_option_element() {
                return "<option onclick='SPARX.Manage.tab_clicked(" + new_tab + ");'>" + new_tab + "</option>";
            }
			var sections = document.getElementById("sections");
			var pages = document.getElementById("pages");
			// tabs.innerHTML = tabs.innerHTML + "<div id='"+new_tab+"_tab' onclick='SPARX.Manage.tab_clicked(event);' class='inactive_tab'><p style='margin:5px auto;width:"+(6.5*new_tab.length)+"px;'>"+new_tab+"</p></div>";
            sections.innerHTML = sections.innerHTML + get_option_element();
			pages.innerHTML = pages.innerHTML + "<div id='"+new_tab+"_page' class='inactive_page'>"+new_tab+" is loading...</div>";
		},
		get_current_active_tab : function(){

		},
		get_current_active_page : function(){
			return current_active_page;
		},

		show_page : function(page){
			var page_name = page + "_page";
			SPARX.Manage.UI.hide_all_pages();
			var page_ele = document.getElementById(page_name);
			if(page_ele){
				page_ele.className = "active_page";
				current_active_page = page_name;
			}
			SPARX.Manage.get_config(page);
		},
		hide_all_pages : function(){
			var pages = document.getElementById("pages");
			var page_list = pages.children;
			for(var i in page_list){
				try{
					page_list[i].className = "inactive_page";
				}catch(e){
					break;
				}
			}
		},
		hide : function(event){
			if(typeof(event) === "string"){
				var ele = document.getElementById(event);
				if(ele)
					ele.style.display = "none";

			}
			document.getElementById("popup").style.display = "none";
		},
		selector_move : function(to, from){
			var to_ele = document.getElementById(to);
			var from_ele = document.getElementById(from);
			from_option_list = from_ele.children;
			var new_from_ele_html = "";
			var new_data = "";
			for(var i in from_option_list){
				if(from_option_list[i].tagName == "OPTION"){
					if(from_option_list[i].selected == true){
						to_ele.innerHTML = to_ele.innerHTML + "<option value='"+from_option_list[i].value+"'>"+from_option_list[i].innerHTML+"</option>";
						new_data = from_option_list[i].value;
					}
					else{
						new_from_ele_html = new_from_ele_html + "<option value='"+from_option_list[i].value+"'>"+from_option_list[i].innerHTML+"</option>";
					}
				}
			}
			from_ele.innerHTML = new_from_ele_html;
			return {"to":to, "data":new_data, "from": from};
		},
		add_to : function(to, from_ele){
			var to_ele = document.getElementById(to);
			if(typeof(from_ele) === "string")
				var from_ele = document.getElementById(from_ele);
			to_ele.innerHTML = to_ele.innerHTML + "<option value='"+from_ele.value+"'>"+from_ele.value+"</option>";
			var new_data = from_ele.value
			from_ele.value = "";
			return {"to":to, "data":new_data};
		},
	}
}();

function syntaxHighlight(section, json) {
    if (typeof json != 'string') {
         json = JSON.stringify(json, undefined, 2);
    }
    var id = "";
    var keys = [];
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)|{|}|,/g, function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
                id = match.slice(1,-2);
                return '<li class="' + cls + '">' + match.slice(1,-2)+":" + '';
            } else {
                cls = 'string';
                keys.push(id);
                return '<input type="text" id='+id+' class="' + cls + '" value=' + match + ' onkeypress="if(event.keyIdentifier == \'Enter\'){SPARX.Manage.new_data(\''+section+'\',\''+keys+'\' ,event.currentTarget.value);}"></input></li>';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        else if (/{/.test(match)){
            if(id)
                keys.push(id);
            return '<ol>';
        }
        else if (/}/.test(match)){
            keys = [];
            return '</ol>';
        }
        else if (/,/.test(match)){
            keys = keys.slice(0, -1);
            return '';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}
