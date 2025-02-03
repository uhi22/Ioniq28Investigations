/* This SavvyCAN script sends the CAN messages to the VESS, to
    simulate a driving vehicle. We change the speed continuously between
    30km/h forward and 30km/h reverse. */
var speed = 0; /* in 1/256km/h */
var speedgradient=50; // in 1/256km/h per 100ms
var printdivider=0;
var gearselect;

function setup ()
{
  host.setTickInterval(100); /* The VESS stops the sound if it does not see a message for ~500ms.
                                            So we send it in 100ms to be on the safe side. */
  can.setFilter(0x0, 0, 0); /* just in case we want to evaluate some receive messages. */
}

function tick()
{
  // From the Kona:
  //200 : 00 28 00 10 00 3B D0 00 for gear
  //524 : 60 01 02 40 5A 01 C0 02 for speed
  if (speed>0) gearselect=0xA8; else gearselect=0xB8; /* from the Ioniq log */
  can.sendFrame(0, 0x200, 8, [0x00, gearselect, 0x00, 0x10, 0x00, 0x3B, 0xD0, 0x00]);
  var absSpeed = speed;
  if (absSpeed<0) absSpeed=-absSpeed; /* we need positive speed, even in reverse direction */
  can.sendFrame(0, 0x524, 8, [0x60, 0x01, absSpeed>>8, absSpeed & 0xff, 0x5A, 0x01, 0xC0, 0x02]);

  speed=speed+speedgradient; /* change the speed */
  if (speed>30*256) {  speedgradient=-50; } /* if we are fast, we want to slow down */
  if (speed<-30*256) {  speedgradient=50; } /* if we are fast in reverse, we want to slow down */
  printdivider++;
  if (printdivider>=5) { /* print the speed to console, but do not spam too much */
    host.log("speed " + speed/256 + " km/h");
    printdivider=0;
  }
}