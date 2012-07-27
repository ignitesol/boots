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
			tuneid = signal.tuneid.split('@')[1];
			cid = signal.tuneid.split('@')[0];
		} catch(e) {
			console.log(e);
			return;
		}
		
		return [cid, tuneid, signal];
	}
	
	var sparx_dmsg = {
		get plugin_type() { return 'receive'},
		get apply() { return _apply; }
	};
	
	// inheritance
	utils.inherit(sparx_dmsg, ZMQBasePlugin);
	
	return sparx_dmsg;
}

// Exports
var Plugins = {};
Plugins.SPARXDeMessage = SPARXDeMessage;

module.exports = Plugins;
