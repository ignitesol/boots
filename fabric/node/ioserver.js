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
		// socket_server.logger.info('expiring', id);
		if (client_eps[id]) {
			client_eps[id].close();
			delete client_eps[id];
		}
	}
	
	function _on_disconnect(client) {
		// socket_server.logger.info('disconnected', client.id);
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
		var room_list = [];
		
		utils.foreach(rooms, function (k, v) {
			if (v.has(id)) room_list.push(v);
		});
		return room_list;
	}
	
	function _close_room(name) {
		rooms[name].close();
		delete rooms[name];
	}
	
	function _disconnect_callback(fn) {
		dc_callback = fn;
	}
	
	/**
	 * HouseKeeping, synchronise socketio and fabric data structures :(
	 * 	When should we do this, is it best suited as a CRON job
	 */
	function _drop_ghost_rooms() {
		var ghosts = [];
		utils.foreach(rooms, function(k, v) {
			if (!connect_ep.socketio.rooms[v.internal_name]) {
				v.close();
				delete rooms[k];
				ghosts.push(k);
			}
		});
		return ghosts;
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
	  , get drop_ghost_rooms() { return _drop_ghost_rooms; }
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
