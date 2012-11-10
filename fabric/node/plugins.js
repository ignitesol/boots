var utils = require('./utils.js');

/**
 * ZMQ Plugins
 */

/**
 * The ZMQ base plugin object
 * Plugins for ZMQ Endpoints will inherit from this
 * Plugins must implement and expose a
 *  *setup method
 *  *apply method
 * setup will be called when the endpoint is activated
 * apply is called with the message and the return must be what needs
 * to be passed on to subsequent plugins or pushed on to the socket
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

/**
 * Callback Plugin for ZMQ messages received
 * Messages must be a dictionary type object
 * The attribute supplied must match the supplied value, then the callback will be called
 */
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
			/* Do not make this a substring search
			 * Otherwise it sends duplicate messages to tuneids that have subset names
			 * eg: tuneid-2 and tuneid-20 shall both be called for tuneid-2
			 */
			if (typeof(path) === 'string' && path === k) {
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
Plugins.ZMQBasePlugin = ZMQBasePlugin;
Plugins.MessageRoute = MessageRoute;

module.exports = Plugins;
