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

function SPARXMessage(jsonify/*optional*/) {
	// default
	jsonify = jsonify === undefined? true: jsonify;
	
	var message = {
		
	};
	
	// inheritance
	utils.inherit(message, ZMQBasePlugin);
}
