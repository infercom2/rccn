<?

switch ($_REQUEST['service']) {

	case "imei":
		require_once("modules/httpful.phar");
		$path = "http://localhost:8085/subscriber/imei/".$_REQUEST['term'];
		$response = \Httpful\Request::get($path)->expectsJson()->send();
		$data = $response->body;
		//print json_encode($data);
		print '[ ';
		foreach ($data as $key => $value) {
			$s.='"'.substr($value[0],0,14).'X",';

		}
		print rtrim($s,',');
		print ' ]';
	break;
	case "credit":
		require_once("modules/credit.php");
		$cred = new Credit();
		print $cred->get_credit_records($_REQUEST['year']);
	break;
	case "numbers":
		require_once("modules/subscriber.php");
		$sub = new Subscriber();
		$data = $sub->search($_REQUEST['term']);
		print '[ ';
		foreach ($data as $key => $value) {
			$s.='{ "label": "' .$value[0]." - ".$value[1]. '", "value": "'.$value[0].'" }, ';
		}
		print rtrim($s,', ');
		print ' ]';
	break;
}

?>