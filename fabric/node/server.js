var utils = require('./utils.js')
  , endpoints = require('./endpoint.js');

// This will be the exported module
var Fabric = {}

function Server(name, endpoints) {
	// private
	var _endpoints = {}
	  , _logger = console // The default logger
	  ;
	
	function _add_endpoint(ep) {
		_endpoints[ep.uuid] = ep;
	}
	
	function _activate_endpoints() {
		var args_list = utils.listify_arguments(arguments);
		args_list = [server.self].concat(args_list);
		utils.foreach(_endpoints, function(k, v) {
			// For any extra arguments
			v.activate.apply(v, args_list);
		});
	}
	
	function _start_main_server() {
		// ugly hack, self does not exist until constructor returns
		utils.foreach(_endpoints, function(k, v) {
			server.self.add_endpoint(v);
		});
		
		server.self.activate_endpoints();
	}
	
	// public
	var server = {
		add_endpoint: _add_endpoint
	  , activate_endpoints: _activate_endpoints
	  , start_main_server: _start_main_server
	  , get endpoints() { return _endpoints; }
	  , get logger() { return _logger; }
	  , set logger(value) { _logger = value; }
	};
	
	utils.foreach(endpoints, function(k, v) {
		_endpoints[v.uuid] = v;
	});
	
	return server;
}

function ZMQServer(name, endpoints) {
	endpoints = endpoints || [];
	
	// private
	
	// public
	var zmq_server = {
	};
	
	// inheritance
	utils.inherit(zmq_server, Server, [name, endpoints]);
	
	return zmq_server;
}

// Module exports
Fabric.Server = Server;
Fabric.ZMQServer = ZMQServer;
module.exports = Fabric;