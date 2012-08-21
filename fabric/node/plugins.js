var utils = require('./utils.js');

/**
 * ZMQ Plugins
 */

function ZMQBasePlugin() {
	var _plugin_type = null;
	
	var zmq_plugin = {
		plugin_type: _plugin_type,
		setup: function() {},
		apply: function() {}
	};
	
	return zmq_plugin;
}

function SPARXDeMessage(jsonify/*optional*/) {
	// default
	jsonify = jsonify === undefined? true: jsonify;
	
	function _apply(msg) {
		var signal = null;
		var tuneid = null;
		var cid = null;
		
		try {
			signal = JSON.parse(msg[2]);
			if (signal.tuneid) {
				signal.tunenum = signal.tuneid.split('@')[1];
				signal.cid = signal.tuneid.split('@')[0];
			}
		} catch(e) {}
		
		return signal;
	}
	
	var sparx_dmsg = {
		get plugin_type() { return 'receive'},
		get apply() { return _apply; }
	};
	
	// inheritance
	utils.inherit(sparx_dmsg, ZMQBasePlugin);
	
	return sparx_dmsg;
}

function MessageRoute(routes) {
	var _endpoint = null
	  , _routes = routes || {}
	  ;
	
	function _setup(ep) {
		_endpoint = ep;
		if (!ep.from) {
			// ep.from(route).on(fn) 
			//  -- or --
			// ep.from(route).drop()
			ep.__defineGetter__('from', function() { 
				return function (attr, route) {
					return {
						on: function(fn) { msg_route.on(attr, route, fn); },
						drop: function() { msg_route.drop(route); }
					};
				};
			});
		}
	}
	
	function _apply(msg) {
		utils.foreach(_routes, function(k, v) {
			var path = msg[v.key];
			if (typeof(path) === 'string' && path.indexOf(k) === 0) {
				v.callback(msg);
			}
		});
		
		return msg;
	}
	
	function _on(attr, route, fn) {
		_routes[route] = {key: attr, callback: fn};
	}
	
	function _drop(route) {
		delete _routes[route];
	}
		
	var msg_route = {
		get plugin_type() { return 'receive'; },
		get setup() { return _setup; },
		get apply() { return _apply; },
		get on() { return _on; }
	}
	
	utils.inherit(msg_route, ZMQBasePlugin);
	
	return msg_route;
}

// Exports
var Plugins = {};
Plugins.SPARXDeMessage = SPARXDeMessage;
Plugins.MessageRoute = MessageRoute;

module.exports = Plugins;
