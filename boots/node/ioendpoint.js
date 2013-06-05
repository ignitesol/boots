var utils = require('./utils.js')
  , ep = require('./endpoint.js');

/**
 * This endpoint accepts new client connections using socketio
 * It serves as an interface for clients to the server
 */
function IOConnectionEndpoint(_context, _onconnect) {
	// private
	var connection_callback = _onconnect
	  , context = _context
	  , iolib = require('socket.io')
	  , io = null;
	 
	 function _activate(server) {
	 	io = iolib.listen(context);
	 	io.set('log level', 2);
	 	
	 	/* Testing purposes */
	 	// io.set('heartbeat interval', 2);
	 	// io.set('heartbeat timeout', 20);
	 	
	 	io.set('transports', [
                 'websocket'
              // , 'flashsocket'
              // , 'htmlfile'
              // , 'xhr-polling'
              // , 'jsonp-polling'
            ]);
	 	
	 	io.sockets.on('connection', connection_callback);
	 	io_conn.Super.activate(server);
	 }
	
	// public
	var io_conn = {
		activate: _activate,
		onconnect: function(callback) {
			connection_callback = callback;
			io && io.sockets.on('connection', connection_callback);
		},
		get socketio() { return io; }
	};
	
	// inheritance
	utils.inherit(io_conn, ep.EndPoint);
	
	return io_conn;
}

/**
 * This Endpoint serves as an interface for the server to each client
 * One endpoint corresponds to one socketio connection
 */
function IOClientServiceEndpoint(_socket/*optional*/) {
	// private
	var socket = _socket || null;
	var _route_callbacks = {};
	
	function _activate(server, _socket/*optional*/) {
		io_ep.Super.activate(server);
		socket = _socket || socket; // optional, remain the same if nothing given
		utils.foreach(_route_callbacks, function(k, v) {
			socket.on(k, v);
		});
	}
	
	/**
	 * Adds a route to client messages
	 * The callback is invoked everytime a message on that route is received
	 */
	function _add_route_callback(route, callback) {
		_route_callbacks[route] = callback;
		if (socket) socket.on(route, callback);
	}
	
	function _remove_route(route, del_callback) {
		del_callback = del_callback || function(){ };
		delete _route_callbacks[route];
		if (socket) socket.removeListener(route, del_callback);
	}
	
	/**
	 * Close the socket
	 * Remove all listeners and disconnect the socket
	 */
	function _close() {
		if (socket) {
			socket.removeAllListeners();
			socket.disconnect();
		}
	}
	
	function _emit() {
		if (!socket.disconnected) socket.emit.apply(socket, utils.listify_arguments(arguments));
	}
	
	function _join(room_name) {
		if (!socket.disconnected) socket.join(room_name);
	}
	
	function _leave(room_name) {
		if (!socket.disconnected) socket.leave(room_name);
	}
	
	/**
	 * Setup the disconnect callback
	 */
	function _ondisconnect(fn) {
		socket.on('disconnect', function(){ fn(io_ep); });
	}
	
	/**
	 * Store set function
	 */
	function _socket_set() {
		var args = utils.listify_arguments(arguments);
		socket.set.apply(socket, args);
	}
	
	/**
	 * Store retrieve function
	 */
	function _socket_get() {
		var args = utils.listify_arguments(arguments);
		socket.get.apply(socket, args);
	}
	
	// public
	var io_ep = {
		activate: _activate
	  , close: _close
	  , on: _add_route_callback
	  , drop: _remove_route
	  , ondisconnect: _ondisconnect
	  , get id() { return socket? socket.id: null; }
	  , get emit() { return _emit; }
	  , get join() { return _join; }
	  , get leave() { return _leave; }
	  , get disconnected() { return socket.diconnected; }
	  , get namespace() { return socket.namespace.name; }
	  , get store() { return _socket_set }
	  , get retrieve() { return _socket_get }
	};
	
	// inheritance
	utils.inherit(io_ep, ep.EndPoint);
	return io_ep;
}

/**
 * Rooms are managed by Socket IO internally
 * This is simply a wrapped method of getting these grouped sockets
 * It doesn't expose the sockets directly, 
 * but tries to get the Client endpoints for those sockets from its server
 * It does not support namespaces, only the default '/' namespace
 */
function IORoomEndpoint(_io, _name) {
	// private
	var io = _io
	  , name = _name
	  , clients = {}
	  ;
	
	/**
	 * Add a client endpoint to this rooms namespace
	 */
	function _add_client(ep) {
		clients[ep.id] = true;
		ep.join(name);
	}
	
	/**
	 * remove a client from this rooms namespace
	 */
	function _remove_client(ep) {
		delete clients[ep.id];
		ep.leave(name);
	}
	
	/**
	 * Broadcast a message to all clients
	 */
	function _broadcast() {
		var args = utils.listify_arguments(arguments)
		  , these_sockets = io.sockets.in(name)
		  ;
		
		these_sockets.emit.apply(these_sockets, args);
	}
	
	function _real_name() {
		// We dont know what namespace it is part of
		return io.sockets.name + name;
	}
	
	function _clients() {
		// var clients_list = [];
		// utils.foreach(clients, function(k, v) { clients_list.push(k); });
		// return clients_list;
		return io.sockets.clients(name).map(function(c) { return c.id; });
	}
	
	function _has_client(id) {
		return clients[id] !== undefined;
	}
	
	function _close() {
	    var clist = io.sockets.clients(name);
	    // Make all client sockets leave the room
	    clist.forEach(function(v, k) {
	        v.leave(name);
	    });
		room.Super.close();
	}
	
	// public
	var room = {
		get name() { return name; }
	  , get include() { return _add_client; }
 	  , get exclude() { return _remove_client; }
	  , get broadcast() { return _broadcast; }
	  , get clients() { return _clients(); }
	  , get close() { return _close; }
	  , get has() { return _has_client; }
	}
	
	// inheritance
	utils.inherit(room, ep.EndPoint);
	
	return room;
}

// Module Exports
var Exports = {};
Exports.IOConnectionEndpoint = IOConnectionEndpoint;
Exports.IOClientServiceEndpoint = IOClientServiceEndpoint;
Exports.IORoomEndpoint = IORoomEndpoint
module.exports = Exports;