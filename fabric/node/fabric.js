var server = require('./server.js')
  , ioserver = require('./ioserver.js')
  , utils = require('./utils.js')
  , ep = require('./endpoint.js')
  , ioep = require('./ioendpoint.js')
  , plugins = require('./plugins.js')
  ;
  
// Exports
var exports = {};
exports.server = server;
utils.foreach(ioserver, function(k, v) { exports.server[k] = v; });
exports.endpoint = ep;
utils.foreach(ioep, function(k, v) { exports.endpoint[k] = v; });
exports.plugins = plugins;
exports.utils = utils;

module.exports = exports;
