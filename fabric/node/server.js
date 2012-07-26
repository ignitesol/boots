var utils = require('./utils.js')
  , endpoints = require('./endpoint.js');

// This will be the exported module
var Fabric = {}

function Server(name) {
	// private
	var _endpoints = {};
	
	function _add_endpoint(ep) {
		_endpoints[ep.uuid] = ep;
	}
	
	function _activate_endpoints() {
		var args_list = utils.listify_arguments(arguments);
		utils.foreach(_endpoints, function(k, v) {
			// For any extra arguments
			v.activate.apply(v, args_list);
		});
	}
	
	function _start_main_server() {
		server.self.activate_endpoints();
	}
	
	// public
	var server = {
		add_endpoint: _add_endpoint,
		activate_endpoints: _activate_endpoints,
		start_main_server: _start_main_server,
		get endpoints() { return _endpoints; }
	};
	
	return server;
}

function ZMQServer(name, endpoints) {
	endpoints = endpoints || [];
	
	// private
	function _add_endpoint(ep) {
		zmq_server.Super.add_endpoint(ep);
	}
	
	// public
	var zmq_server = {
		add_endpoint: _add_endpoint
	};
	
	// inheritance
	utils.inherit(zmq_server, Server, [name]);
	
	utils.foreach(endpoints, function(k, v) {
		zmq_server.self.add_endpoint(v);
	});
	
	return zmq_server;
}

// Module exports
Fabric.Server = Server;
Fabric.ZMQServer = ZMQServer;
module.exports = Fabric;