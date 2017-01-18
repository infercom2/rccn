<?php 
require_once('include/header.php');
require_once('include/menu.php'); 


			print_menu('platform'); ?>
			<br/><br/><br/>
			<center>
			<a href="network_stats.php?a=3h">Last 3 Hours</a> | <a href="network_stats.php?a=12h">Last 12 Hours</a> | <a href="network_stats.php?a=1d">Daily</a> | <a href="network_stats.php?a=1w">Weekly</a> | <a href="network_stats.php?a=1m">Monthly</a> | <a href="network_stats.php?a=1y">Year</a>
			<br/><br/><br/>
			<?php
				$age = (isset($_GET['a'])) ? $_GET['a'] : '12h';

				$graphs = array('fs_calls','calls','chanr','chans');
				if (file_exists('/var/rhizomatica/rrd/mybts')) {
				  $mybts=explode(' ',file_get_contents('/var/rhizomatica/rrd/mybts'));
				} else {
				  $mybts=array();
                                  for ($i=0;$i<6;$i++) { array_push($mybts,$i); }
				}
				
                                foreach ($mybts as $i) {
				  array_push($graphs,"chans-".$i);
				}
				
				array_push($graphs,  'broken','lur','sms','hlr_onlinereg','hlr_onlinenoreg');
				foreach ($graphs as &$g) {
					echo "<img src='graphs/$g-$age.png' /><br/><br/>";
				}
			?>
			</center>
		</div>
	</body>
</html>
