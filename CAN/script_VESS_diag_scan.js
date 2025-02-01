var did=0xFFFF+1;

function setup ()
{
  can.sendFrame(0, 0x736, 8, [0x02, 0x3E, 0x00, 0, 0, 0, 0, 0]); /* to test: tester present */
  host.setTickInterval(100); 
  can.setFilter(0x0, 0, 0); 
}

function tick()
{
    //did++;
   if (did>0) did--;
    //host.log("sending UDS frame " + did.toString(16));
    can.sendFrame(0, 0x736, 8, [0x03, 0x22, did>>8, did & 0xff, 0, 0, 0, 0]);
}

function gotCANFrame (bus, id, len, data) {
  if (id==0x73E) {
    if (data[1]==0x7F) {
       //host.log("neg for " +  did.toString(16));
    } else {
       host.log("positive for " +  did.toString(16));
       host.log(data[0].toString(16) + " " + data[1].toString(16) + " " + data[2].toString(16) + " " + data[3].toString(16) + " " + data[4].toString(16) + " " + data[5].toString(16) + " " + data[6].toString(16) + " " + data[7].toString(16));
    }
  }
}