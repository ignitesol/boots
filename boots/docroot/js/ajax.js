function request(url, onsuccess, failure, data, handle_as){
	handle_as = handle_as || "text"
	function error_handler(err, ioArgs){
		if (err.dojoType == 'cancel')
			return;
		else
			failure(err, ioArgs);
	}
	if(data)
		var deferred_obj = dojo.xhrPost({ url: url, content : data, handleAs: handle_as, load: onsuccess, error: error_handler });
	else
		var deferred_obj = dojo.xhrGet({ url: url, handleAs: handle_as, load: onsuccess, error: error_handler });

	return deferred_obj;
}
