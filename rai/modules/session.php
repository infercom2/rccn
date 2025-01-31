<?php

class Session {

	public $access;

	public function __construct($logging_in=false) {
		if (session_id() == '') {
			session_start();
		}
		$this->access = new AccessManager();
		if (!$logging_in) {
			$this->access->checkAuth();
		}
	}

	function store($arr) {
		foreach ($arr as $key => $val) {
			if ($val == "" && isset($_SESSION[$key])) { // If it's empty, delete it.
				unset($_SESSION[$key]);
			}
			if(is_array($val)) { # Don't trim an array!
				$_SESSION[$key] = $val;
			} else {
				$_SESSION[$key] = trim($val);
			}
		}
	}
}

class AccessManagerException extends Exception { }

class AccessManager
{
	public $userid = "";
	public $username = "";
	public $password = "";
	public $role = "";
	public $lang = "";
	
	public function login($username, $password, $lang) {
		$this->username = $username;
		$this->password = $password;
		$this->lang = $lang;
		if ($this->checkPwd($username,$password)) {
			$this->initializeSession();
			if (isset($_SESSION['login_goto_uri']) &&
				  !strstr($_SESSION['login_goto_uri'], 'login.php')) {
				header('Location: '.$_SESSION['login_goto_uri']);
			} else {
				header('Location: subscribers.php');
			}
			return true;
		} else {
			return false;
		}
	}


	public function checkPwd($username,$password) {
		require_once(dirname(__FILE__).'/../include/database.php');
				$db_conn = pg_connect(
			" host=".$DB_HOST.
			" dbname=".$DB_DATABASE.
			" user=".$DB_USER.
			" password=".$DB_PASSWORD);
		$result = pg_query("SELECT * from users WHERE username='".pg_escape_string($username)."'");
		if (!$result) {
			return false;
		}
		$row = pg_fetch_row($result);
		$res = false;
		if (password_verify($password, $row[2])) {
			$res = true;
		} else {
			$res = false;
		}
				pg_free_result($result);
				pg_close($db_conn);

		return $res;
	}


	public function initializeSession() {
		$_SESSION['username'] = $this->username;
		$_SESSION['lang'] = (strlen($this->lang) > 2 ) ? $this->lang.'.utf8' : $this->lang."_".strtoupper($this->lang);
		$_SESSION['is_logged'] = 1;
	}

	public function checkAuth() {
		if (!isset($_SESSION['username']) && !isset($_SESSION['is_logged'])) {
				$_SESSION['login_goto_uri']=$_SERVER["REQUEST_URI"];
			header('Location: login.php');
		} 
	}

	public function logout() {
		unset($_SESSION['username']);
		unset($_SESSION['lang']);
		unset($_SESSION['is_logged']);
		header('Location: login.php');
	}
		
}

?>
