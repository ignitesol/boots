var server = require('./server.js')
  , utils = require('./utils.js')
  , ioendpoint = require('./ioendpoint.js');


// Express based server
function ExpressServer(name, endpoints, port) {
	// private
	var express = require('express')
	  , app = express.createServer()
	  ;
	  
	function _start_main_server() {
		express_server.Super.start_main_server();
		app.listen(port);
	}
	
	function _get(route, fn) {
		app.get(route, fn);
	}
	
	// public
	var express_server = {
		start_main_server: _start_main_server,
		get context() { return app; },
		get get() { return _get; }
	}
	
	utils.inherit(express_server, server.Server, [name, endpoints]);
	
	return express_server;
}

// Express and socket.io based server
function WebSocketServer(name, endpoints, port) {
	// defaults
	endpoints = endpoints || [];
	
	// private
	var client_eps = {}
	  , rooms = {}
	  , client_callback = null
	  , dc_callback = function() {}
	  ;
	
	function _start_main_server() {
		// This order is important
		socket_server.self.add_endpoint(connect_ep);
		socket_server.Super.start_main_server();		
	}
	
	function _activate_endpoints() {
		connect_ep.onconnect(_on_connect);
		socket_server.Super.activate_endpoints();
	}
	
	function _on_connect(socket) {
		var client = ioendpoint.IOClientServiceEndpoint(socket);
		client.activate(socket_server);
		client_eps[socket.id] = client;
		client.ondisconnect(_on_disconnect);
		if (client_callback) client_callback(client);
	}
	
	function _expire(id) {
		// console.log('expiring', id);
		if (client_eps[id]) {
			client_eps[id].close();
			delete client_eps[id];
		}
	}
	
	function _on_disconnect(client) {
		// console.log('disconnected', client.id);
		if (dc_callback(client))
			_expire(client.id);
	}
	
	function _new_client_callback(callback) {
		client_callback = callback;
	}
	
	function _create_room(name) {
		if (!rooms[name]) {
			rooms[name] = ioendpoint.IORoomEndpoint(connect_ep.socketio, name);
			rooms[name].activate(socket_server);
		}
		
		return rooms[name];
	}
	
	function _rooms_of(id) {
		var all_rooms = connect_ep.socketio.roomClients[id]
		  , room_list = []
		  , re = RegExp('^'+(client_eps[id].namespace || '/'))
		  ;
		
		if (all_rooms && client_eps[id])
			utils.foreach(all_rooms, function(k, v) {
				// Adjust for namespace and push
				var name = k.replace(re, '');
				if (rooms[name]) // Is this room created by us
					room_list.push(rooms[name]);
			});
		
		return room_list;
	}
	
	function _disconnect_callback(fn) {
		dc_callback = fn;
	}
	
	// public
	var socket_server = {
		activate_endpoints: _activate_endpoints
	  , start_main_server: _start_main_server
	  , get connection_endpoint() { return connect_ep; }
	  , get clients() { return client_eps; }
	  , get rooms() { return rooms; }
	  , get room() { return _create_room; }
	  , get rooms_of(){ return _rooms_of; } // Rooms of a given socket
	  , get onclient() { return _new_client_callback; }
	  , get ondisconnect() { return _disconnect_callback; }
	  , get expire() { return _expire; }
	}
	
	// inheritance
	utils.inherit(socket_server, ExpressServer, [name, endpoints, port]);
	
	// Add default IO Endpoint
	// We cannot rely on Super for this, since at that time we dont have the 'server' running
	var connect_ep = ioendpoint.IOConnectionEndpoint(socket_server.context);
	
	return socket_server;
}

// Exports

var exports = {};
exports.WebSocketServer = WebSocketServer;

module.exports = exports;
