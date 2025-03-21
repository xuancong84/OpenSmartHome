// This code is for NodeMCU-v2 ESP8266

#include <Esp.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <IPAddress.h>
#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#define ELEGANTOTA_USE_ASYNC_WEBSERVER 1
// You MUST also manually modify ~/Arduino/libraries/ElegantOTA/src/ElegantOTA.h, otherwise link will fail
#include <ElegantOTA.h>
#include <NTPClient.h>
#include <DNSServer.h>
#include <WiFiUdp.h>
#include <md5.h>
#include <Hash.h>
#include <stdio.h>
#include <map>
#include "ESPAsyncUDP.h"
#include "server_html.h"

#if __has_include("secret.h")
#include "secret.h" // put your WIFI credentials in this file, or comment this line out
#endif

#define SENSOR_LOG_MAX  120
#define LOGFILE_MAX_SIZE  200000
#define LOGFILE_MAX_NUM  8
#define FlashButtonPIN 0
#define WIFI_NAME_PREFIX "OpenSmartLight"
#define UDP_PORT 18888      // for LAN broadcast and inform own existence
#define TEST_ALIVE 1000000  // interval (in ms) to contact each known node to check whether they are still alive

void blink_halt(){
  while(1){
    digitalWrite(LED_BUILTIN, 1);
    delay(1000);
    digitalWrite(LED_BUILTIN, 0);
    delay(1000);
  }
}

// Saved parameters
float timezone = 8;
unsigned int PIN_CONTROL_OUTPUT = D2;
unsigned int PIN_MOTION_SENSOR = D3;
unsigned int PIN_LED_MASTER = D1;
unsigned int PIN_LED_ADJ = D5;
unsigned int PIN_AMBIENT_PULLUP = D7;
unsigned int PIN_AMBIENT_INPUT = A0;
unsigned int ENABLE_LOG = 0;
unsigned int DARK_TH_LOW = 960;
unsigned int DARK_TH_HIGH = 990;
unsigned int DELAY_ON_MOV = 30000;
unsigned int DELAY_ON_OCC = 20000;
unsigned int OCC_TRIG_TH = 65530;
unsigned int OCC_CONT_TH = 600;
unsigned int MOV_TRIG_TH = 400;
unsigned int MOV_CONT_TH = 250;
unsigned int LED_BEGIN = 100;
unsigned int LED_END = 125;
unsigned int GLIDE_TIME = 800;
String midnight_starts[7] = { "23:00", "23:00", "23:00", "23:00", "00:00", "00:00", "23:00" };
String midnight_stops[7] = { "07:00", "07:00", "07:00", "07:00", "07:00", "07:00", "07:00" };
String smartctl_starts[7] = { "00:00", "00:00", "00:00", "00:00", "00:00", "00:00", "00:00" };
String smartctl_stops[7] = { "23:59", "23:59", "23:59", "23:59", "23:59", "23:59", "23:59" };

// WIFI parameters
#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif

#ifndef WIFI_IP
#define WIFI_IP IPAddress()
#endif

#ifndef WIFI_GATEWAY
#define WIFI_GATEWAY IPAddress()
#endif

#ifndef WIFI_SUBNET
#define WIFI_SUBNET IPAddress()
#endif

#ifndef WIFI_DNS1
#define WIFI_DNS1 IPAddress()
#endif

#ifndef WIFI_DNS2
#define WIFI_DNS2 IPAddress()
#endif

String node_name = "SmartNode01";
String wifi_ssid = WIFI_SSID;             //Enter your WIFI ssid
String wifi_password = WIFI_PASSWORD;     //Enter your WIFI password
IPAddress wifi_IP = WIFI_IP;
IPAddress wifi_gateway = WIFI_GATEWAY;
IPAddress wifi_subnet = WIFI_SUBNET;
IPAddress wifi_DNS1 = WIFI_DNS1;          //optional
IPAddress wifi_DNS2 = WIFI_DNS2;          //optional


AsyncWebServer server(80);
DNSServer *dnsServer = NULL;
const byte DNS_PORT = 53; 
int ambient_level;
int onboard_led_level = 0;
bool is_dark_mode = false;
bool is_smartlight_on = false;
bool onboard_led = false;
bool motion_sensor = false;
bool control_output = false;
bool DEBUG = false;
bool SYSLED = false;
String sensor_log, svr_reply, params_hash, WIFI_NAME=String(WIFI_NAME_PREFIX)+"_"+WiFi.macAddress();

File fp_hist;
int do_glide = 0;
bool reboot = false, restart_wifi = false, update_ntp = false, reset_wifi = false;
unsigned long tm_last_ambient = 0;
unsigned long tm_last_timesync = 0;
unsigned long tm_last_debugon = 0;
unsigned long tm_last_savehist = 0;
unsigned long tm_smartlight_off = 0;

// Define NTP Client to get time
AsyncUDP asyncUDP;
WiFiUDP *ntpUDP = NULL;
NTPClient *timeClient = NULL;
String getTimeString(){
  char buf[16];
  if(!timeClient) return "00:00:00";
  sprintf(buf, "%02d:%02d:%02d", timeClient->getHours(), timeClient->getMinutes(), timeClient->getSeconds());
  return String(buf);
}
String getDateString(bool showDay=true){
  if(!timeClient)
    return showDay?"0000-00-00":"0000-00";
  time_t epochTime = timeClient->getEpochTime();
  struct tm *ptm = gmtime ((time_t *)&epochTime);
  int monthDay = ptm->tm_mday;
  int currentMonth = ptm->tm_mon+1;
  int currentYear = ptm->tm_year+1900;
  char buf[16];
  showDay?sprintf(buf, "%04d-%02d-%02d", currentYear, currentMonth, monthDay):sprintf(buf, "%04d-%02d", currentYear, currentMonth);
  return String(buf);
}
String weekDays[7]={"Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"};
String getWeekdayString(){
  if(!timeClient) return "";
  return weekDays[timeClient->getDay()];
}
String getFullDateTime(){
  if(!timeClient) return "";
  return getDateString()+" ("+getWeekdayString()+") "+getTimeString();
}

String getBoardInfo(){
  FSInfo info;
  LittleFS.info(info);
  return String("FreeHeap: ") + ESP.getFreeHeap() + "; FlashSize: "+ESP.getFlashChipRealSize() + "; FreeSketchSpace: " + ESP.getFreeSketchSpace()
    +"; Speed: "+ESP.getFlashChipSpeed()+"; File system size (bytes): "+info.usedBytes+"/"+info.totalBytes;
}


// Saveable parameters
enum VAL_TYPE{
  T_INT = 0, 
  T_FLOAT = 1,
  T_IP = 2,
  T_STRING = 3
};

std::map <String, std::pair<VAL_TYPE, void*> > g_params = {
  {"PIN_CONTROL_OUTPUT",  {T_INT, &PIN_CONTROL_OUTPUT}},
  {"PIN_MOTION_SENSOR",   {T_INT, &PIN_MOTION_SENSOR}},
  {"PIN_LED_MASTER",      {T_INT, &PIN_LED_MASTER}},
  {"PIN_LED_ADJ",         {T_INT, &PIN_LED_ADJ}},
  {"PIN_AMBIENT_PULLUP",  {T_INT, &PIN_AMBIENT_PULLUP}},
  {"PIN_AMBIENT_INPUT",   {T_INT, &PIN_AMBIENT_INPUT}},
  {"ENABLE_LOG",    {T_INT, &ENABLE_LOG}},
  {"DARK_TH_LOW",   {T_INT, &DARK_TH_LOW}},
  {"DARK_TH_HIGH",  {T_INT, &DARK_TH_HIGH}},
  {"DELAY_ON_MOV",  {T_INT, &DELAY_ON_MOV}},
  {"DELAY_ON_OCC",  {T_INT, &DELAY_ON_OCC}},
  {"OCC_TRIG_TH",   {T_INT, &OCC_TRIG_TH}},
  {"OCC_CONT_TH",   {T_INT, &OCC_CONT_TH}},
  {"MOV_TRIG_TH",   {T_INT, &MOV_TRIG_TH}},
  {"MOV_CONT_TH",   {T_INT, &MOV_CONT_TH}},
  {"LED_BEGIN",     {T_INT, &LED_BEGIN}},
  {"LED_END",       {T_INT, &LED_END}},
  {"GLIDE_TIME",    {T_INT, &GLIDE_TIME}},
  {"wifi_IP",       {T_IP, &wifi_IP}},
  {"wifi_gateway",  {T_IP, &wifi_gateway}},
  {"wifi_subnet",   {T_IP, &wifi_subnet}},
  {"wifi_DNS1",     {T_IP, &wifi_DNS1}},
  {"wifi_DNS2",     {T_IP, &wifi_DNS2}},
  {"wifi_ssid",     {T_STRING, &wifi_ssid}},
  {"wifi_password", {T_STRING, &wifi_password}},
  {"node_name",     {T_STRING, &node_name}},
  {"timezone",      {T_FLOAT, &timezone}},
  {"midnight_start0", {T_STRING, &midnight_starts[0]}},
  {"midnight_stop0",  {T_STRING, &midnight_stops[0]}},
  {"midnight_start1", {T_STRING, &midnight_starts[1]}},
  {"midnight_stop1",  {T_STRING, &midnight_stops[1]}},
  {"midnight_start2", {T_STRING, &midnight_starts[2]}},
  {"midnight_stop2",  {T_STRING, &midnight_stops[2]}},
  {"midnight_start3", {T_STRING, &midnight_starts[3]}},
  {"midnight_stop3",  {T_STRING, &midnight_stops[3]}},
  {"midnight_start4", {T_STRING, &midnight_starts[4]}},
  {"midnight_stop4",  {T_STRING, &midnight_stops[4]}},
  {"midnight_start5", {T_STRING, &midnight_starts[5]}},
  {"midnight_stop5",  {T_STRING, &midnight_stops[5]}},
  {"midnight_start6", {T_STRING, &midnight_starts[6]}},
  {"midnight_stop6",  {T_STRING, &midnight_stops[6]}},

  {"smartctl_start0", {T_STRING, &smartctl_starts[0]}},
  {"smartctl_stop0",  {T_STRING, &smartctl_stops[0]}},
  {"smartctl_start1", {T_STRING, &smartctl_starts[1]}},
  {"smartctl_stop1",  {T_STRING, &smartctl_stops[1]}},
  {"smartctl_start2", {T_STRING, &smartctl_starts[2]}},
  {"smartctl_stop2",  {T_STRING, &smartctl_stops[2]}},
  {"smartctl_start3", {T_STRING, &smartctl_starts[3]}},
  {"smartctl_stop3",  {T_STRING, &smartctl_stops[3]}},
  {"smartctl_start4", {T_STRING, &smartctl_starts[4]}},
  {"smartctl_stop4",  {T_STRING, &smartctl_stops[4]}},
  {"smartctl_start5", {T_STRING, &smartctl_starts[5]}},
  {"smartctl_stop5",  {T_STRING, &smartctl_stops[5]}},
  {"smartctl_start6", {T_STRING, &smartctl_starts[6]}},
  {"smartctl_stop6",  {T_STRING, &smartctl_stops[6]}}

};

std::map <String, std::pair<String, unsigned long> > g_nodeList;
std::map <String, unsigned long> g_nodeLastPing;

bool set_value(String varname, String val_str){
  if(DEBUG) Serial.println("Setting '"+varname+"' to '"+val_str+"'");
  auto it = g_params.find(varname);
  if(it==g_params.end()){
    if(DEBUG) Serial.println("Cannot find variable `"+varname+"'");
    return false;
  }
  void *pp = it->second.second;
  switch(it->second.first){
    case T_INT:     *(int*)pp = val_str.toInt();    break;
    case T_FLOAT:   *(float*)pp = val_str.toFloat();break;
    case T_STRING:  *(String*)pp = val_str;         break;
    case T_IP:
      IPAddress ipa;
      if(!ipa.fromString(val_str)) return false;
      *(IPAddress*)pp = ipa;
  }
  if(varname=="node_name" && WiFi.isConnected()){
    g_nodeList[WiFi.localIP().toString()].first = node_name;
    udpBroadcast();
  }
  // update_hash();
  return true;
}

bool set_times(String prefix, String s){
  if(DEBUG)
    Serial.println("Setting "+prefix+" to "+s);
  String tms[7];
  for(int x=0; x<7; x++){
    int posi = s.indexOf(' ');
    if(posi<0 && x<6) return false;
    tms[x] = posi<0?s:s.substring(0, posi);
    s = s.substring(posi+1);
  }
  for(int x=0; x<7; x++)
    if(!set_value(prefix+x, tms[x]))
      return false;
  // update_hash();
  return true;
}

void append_prune(String &buf, const String &s, int max_size){
  if(s.isEmpty()) return;
  while(buf.length() + s.length() > max_size){
    int posi = buf.indexOf('\n');
    if(posi<0) buf.clear();
    else buf.remove(0, posi+1);
  }
  buf.concat(s+"\n");
}

void open_logfile_auto_rotate(){
  if(!fp_hist.isFile())
    fp_hist = LittleFS.open("/0.log", "a");
  if(fp_hist.size()>LOGFILE_MAX_SIZE){  // rotate log
    fp_hist.close();
    for(int x=LOGFILE_MAX_NUM-1; x>=0; x--)
      LittleFS.rename("/"+String(x)+".log", "/"+String(x+1)+".log");
    LittleFS.remove("/"+String(LOGFILE_MAX_NUM)+".log");
    fp_hist = LittleFS.open("/0.log", "a");
  }
}

void log_event(const char *event){
  if(!ENABLE_LOG) return;
  open_logfile_auto_rotate();
  String fullDateTime = getFullDateTime();
  fp_hist.printf("%s : %s\n", fullDateTime.c_str(), event);
  fp_hist.flush();
}

void md5(char *out, char *buf, int len) {
  md5_context_t ctx;
  MD5Init(&ctx);
  MD5Update(&ctx, (const uint8_t*)buf, len);
  MD5Final((uint8_t*)out, &ctx);
}

bool save_file(const char *filename, const char *buf, size_t length){
  File fp = LittleFS.open(filename, "w");
  if(fp.isFile()){
    size_t n_written = fp.write((uint8_t*)buf, length);
    fp.close();
    return n_written==length;
  }
  return false;
}

void add_config(JsonObject &obj){
  for(auto it=g_params.begin(); it!=g_params.end(); ++it){
    String name = it->first;
    void *pp = it->second.second;
    switch(it->second.first){
      case T_INT:     obj[name] = *(int*)pp;    break;
      case T_FLOAT:   obj[name] = *(float*)pp;  break;
      case T_STRING:  obj[name] = *(String*)pp; break;
      case T_IP:      obj[name] = ((IPAddress*)pp)->toString(); break;
    }
  }
}

bool save_config(){
  File fp = LittleFS.open("/config.json", "w");
  DynamicJsonDocument doc(2048);
  JsonObject obj = doc.to<JsonObject>();
  add_config(obj);
  serializeJson(doc, fp);
  fp.close();
  return true;
}

bool load_config(){
  // test whether the config file is valid
  File fp = LittleFS.open("/config.json", "r");
  if(!fp.isFile()) return false;
  DynamicJsonDocument doc(2048);
  DeserializationError err = deserializeJson(doc, fp);
  fp.close();
  if(err != DeserializationError::Ok){
    if(DEBUG) Serial.println(String("Error: deserializeJson failed with error ")+err.f_str());
    return false;
  }

  // load the config file
  int n_success = 0;
  for(auto it=g_params.begin(); it!=g_params.end(); ++it)
    if(doc.containsKey(it->first)) if(set_value(it->first, doc[it->first])) n_success++;
  if(n_success!=g_params.size() && DEBUG)
    Serial.printf("Not all parameters loaded successfully: only %d out of %d\n", n_success, g_params.size());
  
  return true;
}

void set_output(bool state){
  digitalWrite(PIN_CONTROL_OUTPUT, state?1:0);
  control_output = state;
  log_event(state?"light on":"light off");
  if(DEBUG) Serial.printf("Output = %s\n", state?"On":"Off");
}

void set_sensor(bool state){
  digitalWrite(PIN_MOTION_SENSOR, state?1:0);
  motion_sensor = state;
  log_event(state?"sensor on":"sensor off");
  if(DEBUG) Serial.printf("Sensor = %s\n", state?"On":"Off");
}

void set_onboard_led(bool state){
  digitalWrite(PIN_LED_MASTER, state?1:0);
  onboard_led = state;
  if(DEBUG) Serial.printf("Onboard LED = %s\n", state?"On":"Off");
}

void glide_onboard_led(bool state){
  log_event(state?"glide LED on":"glide LED off");
  if(GLIDE_TIME==0){
    set_onboard_led(state);
    onboard_led_level = state?LED_END:LED_BEGIN;
    analogWrite(PIN_LED_ADJ, onboard_led_level);
    return;
  }
  int level;
  float spd = ((float)GLIDE_TIME)/((LED_BEGIN+LED_END+1)*(abs(int(LED_END-LED_BEGIN))+1)/2);
  if(state){  // turn on gradually
    analogWrite(PIN_LED_ADJ, LED_BEGIN);
    digitalWrite(PIN_LED_MASTER, 1);
    for(level=LED_BEGIN; level<=LED_END; level++){
      delay((unsigned long)(level*spd));
      analogWrite(PIN_LED_ADJ, level);
    }
  }else{  // turn off gradually
    analogWrite(PIN_LED_ADJ, LED_END);
    for(level=LED_END; level>=LED_BEGIN; level--){
      delay((unsigned long)(level*spd));
      analogWrite(PIN_LED_ADJ, level);
    }
    digitalWrite(PIN_LED_MASTER, 0);
    analogWrite(PIN_LED_ADJ, 0);
  }
  onboard_led = state;
  onboard_led_level = level;

  if(DEBUG) Serial.printf("Onboard LED gradually turned %s to %d\n", state?"ON":"OFF", level);
}

void set_onboard_led_level(int level){
  analogWrite(PIN_LED_ADJ, level);
  onboard_led_level = level;
  if(DEBUG) Serial.printf("Onboard LED level = %d\n", level);
}

void set_debug(bool state){
  digitalWrite(LED_BUILTIN_AUX, !state);
  DEBUG = state;
  Serial.printf("DEBUG LED state = %d\n", DEBUG);
  if(state) tm_last_debugon = millis();
}

void set_system_led(bool state){
  digitalWrite(LED_BUILTIN, !state);
  SYSLED = state;
  if(DEBUG) Serial.printf("System LED state = %d\n", SYSLED);
}

void set_system_led_level(int value){
  int level = 255-value;
  level = min(255, max(0, level));
  analogWrite(LED_BUILTIN, level);
  SYSLED = value>0;
  if(DEBUG) Serial.printf("System LED level = %d\n", value);
}

boolean isIp(String str) {
  for (size_t i = 0; i < str.length(); i++) {
    int c = str.charAt(i);
    if (c != '.' && (c < '0' || c > '9'))
      return false;
  }
  return true;
}

void smartlight_off(){
  log_event("smartlight off");
  if(control_output) set_output(false);
  if(onboard_led) glide_onboard_led(false);
  is_smartlight_on = false;
}

bool is_midnight(){
  int weekday = (timeClient->getDay()+6)%7;
  String midnight_start = midnight_starts[weekday], midnight_stop = midnight_stops[weekday];
  int hours = timeClient->getHours(), minutes = timeClient->getMinutes();
  String midnight_time = getTimeString().substring(0, 5);
  if(midnight_start.isEmpty() || midnight_stop.isEmpty()) return false;
  if(midnight_stop > midnight_start) // midnight starts after 0am
    return midnight_time>=midnight_start && midnight_time<=midnight_stop;
  return midnight_time>=midnight_start || midnight_time<=midnight_stop;
}

bool is_smartctl(){
  int weekday = (timeClient->getDay()+6)%7;
  String smartctl_start = smartctl_starts[weekday], smartctl_stop = smartctl_stops[weekday];
  int hours = timeClient->getHours(), minutes = timeClient->getMinutes();
  String smartctl_time = getTimeString().substring(0, 5);
  if(smartctl_start.isEmpty() || smartctl_stop.isEmpty()) return false;
  if(smartctl_stop > smartctl_start) // midnight starts after 0am
    return smartctl_time>=smartctl_start && smartctl_time<=smartctl_stop;
  return smartctl_time>=smartctl_start || smartctl_time<=smartctl_stop;
}

void smartlight_on(){
  log_event("smartlight on");
  is_midnight() ? glide_onboard_led(true) : set_output(true);
  is_smartlight_on = true;
}

void handleRoot(AsyncWebServerRequest *request) {
  if(dnsServer && !isIp(request->host())){
    AsyncWebServerResponse *response = request->beginResponse(302, "text/plain", "");
    response->addHeader("Location", "http://" + request->client()->localIP().toString());
    request->send(response);
    request->client()->stop();
    return;
  }
  request->send_P(200, "text/html", server_html);
}

void add_status(JsonObject &obj, JsonObject &obj1){
  obj["datetime"] = getFullDateTime();
  obj["dbg_led"] = DEBUG;
  obj["sys_led"] = SYSLED;
  obj["ambient"] = ambient_level;
  obj["motion_sensor"] = motion_sensor;
  obj["onboard_led"] = onboard_led;
  obj["onboard_led_level"] = onboard_led_level;
  obj["control_output"] = control_output;
  obj["sensor_output"] = sensor_log;
  obj["is_midnight"] = is_midnight();
  obj["is_smartctl"] = is_smartctl();
  obj["board_info"] = getBoardInfo();
  for(auto it=g_nodeList.begin(); it!=g_nodeList.end(); ++it)
    obj1[it->first] = it->second.first;
  obj["node_list"] = obj1;
  if(!svr_reply.isEmpty()){
    obj["svr_reply"] = svr_reply;
    svr_reply = "";
  }
  obj["this_ip"] = WiFi.localIP().toString();
}

void handleStatus(AsyncWebServerRequest *request){
  DynamicJsonDocument doc(2048), doc1(1024);
  JsonObject obj = doc.to<JsonObject>(), obj1 = doc1.to<JsonObject>();
  add_status(obj, obj1);
  String output;
  serializeJson(doc, output);
  request->send(200, "text/html", output);
}

void handleStatic(AsyncWebServerRequest *request){
  DynamicJsonDocument doc(2048), doc1(1024);
  JsonObject obj = doc.to<JsonObject>(), obj1 = doc1.to<JsonObject>();
  add_config(obj);
  add_status(obj, obj1);
  String output;
  serializeJson(doc, output);
  request->send(200, "text/html", output);
}

bool hotspot(){
  IPAddress apIP(172, 0, 0, 1);
  log_event("Creating hotspot with captive portal ...");
  Serial.println("Creating hotspot 'OpenSmartLight' ...");
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0));
  WiFi.softAP(WIFI_NAME);
  Serial.print("Hotspot IP address: ");
  Serial.println(apIP);
  dnsServer = new DNSServer();
  dnsServer->setErrorReplyCode(DNSReplyCode::NoError);
  dnsServer->start(DNS_PORT, "*", apIP);
  initNTP();
  return false;
}

void initNTP(){
  if(timeClient){
    timeClient->end();
    delete timeClient;
  }
  if(ntpUDP){
    ntpUDP->stop();
    delete ntpUDP;
  }
  ntpUDP = new WiFiUDP();
  timeClient = new NTPClient(*ntpUDP, "pool.ntp.org", timezone*3600, 7200);
  timeClient->begin();
  timeClient->update();
  log_event((String("Synchronize time ")+(timeClient->isTimeSet()?"successfully":"failed")).c_str());
  Serial.printf("Current datetime = %s\n", getFullDateTime().c_str());
}

bool initWifi(){
  g_nodeList.clear();
  if(dnsServer){
    dnsServer->stop();
    delete dnsServer;
    dnsServer = NULL;
  }

  if(wifi_ssid.isEmpty())
    return hotspot();

  Serial.print("Connecting to WiFi ...");

  // Configures static IP address
  WiFi.mode(WIFI_STA);
  if (!WiFi.config(wifi_IP, wifi_gateway, wifi_subnet, wifi_DNS1.isSet()?wifi_DNS1:IPAddress(0), wifi_DNS2.isSet()?wifi_DNS2:IPAddress(0)))
    Serial.println("Static IP settings not set or incorrect: DHCP will be used");

  WiFi.begin(wifi_ssid, wifi_password);
  for(int x=0; x<=60; ++x){
    if(WiFi.status() == WL_CONNECTED) break;
    delay(1000);
    Serial.print(".");
  }
  if(WiFi.status() == WL_CONNECTED){
    log_event((String("Connected to WIFI, SSID=")+wifi_ssid).c_str());
    Serial.println("\nWiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());
  }else{
    log_event((String("Failed to connect to WIFI, SSID=")+wifi_ssid).c_str());
    Serial.println("\nUnable to connect to WiFi");
    return hotspot();
  }

  // Update time from Internet
  initNTP();
  return true;
}

String getFileList(){
  String ret;
  Dir dir = LittleFS.openDir("/");
  while (dir.next()){
    if(dir.fileName().endsWith(".log"))
      ret += dir.fileName()+" ";
  }
  ret.trim();
  return ret;
}

void deleteALL(){
  Dir dir = LittleFS.openDir("/");
  while (dir.next()){
    if(dir.fileName().endsWith(".log"))
      LittleFS.remove(dir.fileName());
  }
}

String get_udp_bc_msg(){
  DynamicJsonDocument doc(1024);
  doc["APP"] = WIFI_NAME_PREFIX;
  doc["node_name"] = node_name;
  doc["node_ip"] = WiFi.localIP().toString();
  String udp_bc_msg;
  serializeJson(doc, udp_bc_msg);
  return udp_bc_msg;
}

void udpBroadcast(){
  String udp_bc_msg = get_udp_bc_msg();
  if(DEBUG) Serial.println("UDP broadcasting msg: "+udp_bc_msg);
  asyncUDP.broadcastTo(udp_bc_msg.c_str(), UDP_PORT);
}

void inform_node_auto(const String &ip, bool force=false){
  IPAddress ipa;
  if(!ipa.fromString(ip)) return;
  unsigned long tm = millis();
  if(force || g_nodeLastPing.find(ip)==g_nodeLastPing.end() || tm-g_nodeLastPing[ip]>8000){
    String udp_bc_msg = get_udp_bc_msg();
    AsyncUDPMessage udp_msg;
    udp_msg.write((const uint8_t*)udp_bc_msg.c_str(), udp_bc_msg.length());
    asyncUDP.sendTo(udp_msg, ipa, UDP_PORT);
    g_nodeLastPing[ip] = tm;
  }
}

void udpListen(){
  if(asyncUDP.listen(UDP_PORT)){
    asyncUDP.onPacket([](AsyncUDPPacket packet) {
      if(DEBUG)
        Serial.printf("Received UDP from %s:%u (%u bytes)\n", packet.remoteIP().toString().c_str(), packet.localPort(), packet.length());
      DynamicJsonDocument doc(1024);
      if(deserializeJson(doc, packet.data())!=DeserializationError::Ok) return;
      if(doc["APP"]!=WIFI_NAME_PREFIX) return;
      if(!doc.containsKey("node_ip") || !doc.containsKey("node_name")) return;
      
      // check for valid IP
      String node_ip = doc["node_ip"];
      String node_name = doc["node_name"];
      IPAddress ipa;
      if(!ipa.fromString(node_ip)) return;

      if(g_nodeList.find(node_ip)==g_nodeList.end()){ // not found in nodelist
        g_nodeList[node_ip] = std::make_pair(node_name, millis());
        if(DEBUG)
          Serial.println("New OpenSmart node added: "+node_ip+" "+g_nodeList[node_ip].first);
      }else{  // existing node, update node_name and reply if not too frequent
        if(g_nodeList[node_ip].first!=node_name) g_nodeList[node_ip].first = node_name;
      }
      inform_node_auto(node_ip);
      g_nodeList[node_ip].second = millis();
    });
    if(DEBUG) Serial.println("UDP listening on Port "+String(UDP_PORT));
  }
}

void initServer(){
  server.on("/", handleRoot);
  server.on("/status", handleStatus);
  server.on("/static", handleStatic);
  server.on("/reboot", [](AsyncWebServerRequest *request) {reboot = true; request->send(200, "text/html", "");});
  server.on("/restart_wifi", [](AsyncWebServerRequest *request) {restart_wifi = true; request->send(200, "text/html", "");});
  server.on("/update_time", [](AsyncWebServerRequest *request) {update_ntp=true; request->send(200, "text/html", "");});
  server.on("/dbg_led_on", [](AsyncWebServerRequest *request) {set_debug(true);request->send(200, "text/html", "");});
  server.on("/dbg_led_off", [](AsyncWebServerRequest *request) {set_debug(false);request->send(200, "text/html", "");});
  server.on("/sys_led_on", [](AsyncWebServerRequest *request) {set_system_led(true);request->send(200, "text/html", "");});
  server.on("/sys_led_off", [](AsyncWebServerRequest *request) {set_system_led(false);request->send(200, "text/html", "");});
  server.on("/sys_led_level", [](AsyncWebServerRequest *request) {
    if(request->hasArg("level")){
      set_system_led_level(request->arg("level").toInt());
      request->send(200, "text/html", "");
    }else
      request->send(400, "text/html", "");
  });
  server.on("/log_history", [](AsyncWebServerRequest *request) {
    if(request->hasArg("delete")){
      String fn = request->arg("delete");
      if(fn=="ALL") deleteALL();
      else LittleFS.remove(fn);
    }
    request->send(200, "text/html", getFileList());
  });

  server.on("/control_output_on", [](AsyncWebServerRequest *request) {set_output(true);request->send(200, "text/html", "");});
  server.on("/control_output_off", [](AsyncWebServerRequest *request) {set_output(false);request->send(200, "text/html", "");});
  server.on("/motion_sensor_on", [](AsyncWebServerRequest *request) {set_sensor(true);request->send(200, "text/html", "");});
  server.on("/motion_sensor_off", [](AsyncWebServerRequest *request) {set_sensor(false);request->send(200, "text/html", "");});
  server.on("/glide_led_on", [](AsyncWebServerRequest *request) {do_glide=1;request->send(200, "text/html", "");});
  server.on("/glide_led_off", [](AsyncWebServerRequest *request) {do_glide=-1;request->send(200, "text/html", "");});
  server.on("/save_config", [](AsyncWebServerRequest *request) {request->send(200, "text/html", save_config()?"Success":"Failed");});
  server.on("/load_config", [](AsyncWebServerRequest *request) {request->send(200, "text/html", load_config()?"Success":"Failed");});
  server.on("/ENABLE_LOG_on", [](AsyncWebServerRequest *request) {ENABLE_LOG=1;request->send(200, "text/html", "");});
  server.on("/ENABLE_LOG_off", [](AsyncWebServerRequest *request) {ENABLE_LOG=0;request->send(200, "text/html", "");});
  server.on("/onboard_led_on", [](AsyncWebServerRequest *request) {set_onboard_led(true);request->send(200, "text/html", "");});
  server.on("/onboard_led_off", [](AsyncWebServerRequest *request) {set_onboard_led(false);request->send(200, "text/html", "");});
  server.on("/onboard_led_level", [](AsyncWebServerRequest *request) {
    if(request->hasArg("level")){
      set_onboard_led_level(request->arg("level").toInt());
      request->send(200, "text/html", "");
    }else
      request->send(400, "text/html", "");
  });
  server.on("/set_value", [](AsyncWebServerRequest *request) {
    request->send(200, "text/html", set_value(request->argName(0), request->arg((size_t)0))?"Success":"Failed");
  });
  server.on("/set_times", [](AsyncWebServerRequest *request){
    request->send(200, "text/html", set_times(request->argName(0), request->arg((int)0))?"Success":"Failed");
  });
  server.onNotFound([](AsyncWebServerRequest *request){request->send(404, "text/plain", "Content not found.");});
  server.serveStatic("/logs/", LittleFS, "/");
  server.begin();
  ElegantOTA.begin(&server);
  g_nodeList[WiFi.localIP().toString()] = std::make_pair(node_name, millis());
  udpListen();
  udpBroadcast();
  Serial.println("HTTP server started");
}

int readAmbient(){
  unsigned int sum = 0;
  for(int x=0; x<8; x++)
    sum += analogRead(PIN_AMBIENT_INPUT);
  return sum/8;
}

float parse_output_value(String s){
  char posi = s.lastIndexOf(' ');
  if(posi<0)return 0;
  return s.substring(posi+1).toFloat();
}

void IRAM_ATTR handleInterrupt() {
  reset_wifi = true;
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(LED_BUILTIN_AUX, OUTPUT);
  pinMode(PIN_CONTROL_OUTPUT, OUTPUT);
  pinMode(PIN_MOTION_SENSOR, OUTPUT);
  pinMode(PIN_LED_MASTER, OUTPUT);
  pinMode(PIN_LED_ADJ, OUTPUT);
  pinMode(PIN_AMBIENT_PULLUP, INPUT_PULLUP);
  pinMode(PIN_AMBIENT_INPUT, INPUT);

  digitalWrite(LED_BUILTIN, 0);
  digitalWrite(LED_BUILTIN_AUX, 0);

  // Initialize the file-system and create logfile
  LittleFS.begin();

  // Initialize serial
  Serial.begin(115200);
  Serial.setTimeout(100L);
  Serial.println("\nSystem initialized:");

  // Load config file and history file if exist
  bool config_loaded = load_config();
  Serial.println(config_loaded?"Config file is valid and loaded!":"Config file NOT loaded!");
  log_event(config_loaded?"Config file loaded":"Config file NOT loaded");
  digitalWrite(LED_BUILTIN_AUX, config_loaded);

  initWifi();
  log_event("System started");
  initServer();
  digitalWrite(LED_BUILTIN, 1);
  digitalWrite(LED_BUILTIN_AUX, 1);

  if(DEBUG){
    delay(1000);
    set_debug(true);
  }
  // pinMode(FlashButtonPIN, INPUT_PULLUP);
  // attachInterrupt(digitalPinToInterrupt(FlashButtonPIN), handleInterrupt, FALLING);
}

unsigned long elapse = millis();
void loop() {
  unsigned long tm_curr = millis();

  // Update ambient level
  if(tm_curr-tm_last_ambient>1000){
    ambient_level = readAmbient();
    tm_last_ambient = tm_curr;
  }

  // Synchronize Internet time
  if(tm_curr-tm_last_timesync>3600000*24 || update_ntp){
    bool res = timeClient->forceUpdate();
    svr_reply = res?"Success":"Failed";
    log_event((String("Force synchronize time ")+(res?"successfully":"failed")).c_str());
    if(DEBUG){
      Serial.printf("Update NTP %s\n", res?"successfully":"failed");
      Serial.printf("Current datetime = %s\n", getFullDateTime().c_str());
    }
    tm_last_timesync = tm_curr;
    update_ntp = false;
  }

  // Handle reboot
  if(reboot){
    log_event("System reboot");
    delay(200);
    ESP.restart();
  }

  // Handle restart WIFI
  if(restart_wifi){
    restart_wifi = false;
    delay(200);
    WiFi.disconnect(false, true);
    initWifi();
  }

  if(reset_wifi){
    reset_wifi = false;
    wifi_ssid = "";
    WiFi.disconnect(false, true);
    initWifi();
  }

  // Handle glide
  if(do_glide!=0){
    glide_onboard_led(do_glide>0);
    do_glide = 0;
  }

  // Auto disable debug
  if(DEBUG && tm_curr-tm_last_debugon>1800000){
    set_debug(false);
  }

  // Contact each known node to test whether still alive
  if(g_nodeList.size()>1){
    for(auto it=g_nodeList.begin(); it!=g_nodeList.end(); ++it)
      if(it->first!=WiFi.localIP().toString() && tm_curr-it->second.second>=TEST_ALIVE){
        if(tm_curr-it->second.second > TEST_ALIVE+30000){
          g_nodeList.erase(it);
          break;
        }else inform_node_auto(it->first);
      }
  }

  // Receive data from motion sensor
  int s_mask = 0;
  while(Serial.available()){
    String s = Serial.readStringUntil('\n');
    s.trim();
    append_prune(sensor_log, s, SENSOR_LOG_MAX);
    if(s.startsWith("mov") && parse_output_value(s)>=MOV_CONT_TH) s_mask |= 1;
    if(s.startsWith("occ") && parse_output_value(s)>=OCC_CONT_TH) s_mask |= 2;
    if((s.startsWith("mov") && parse_output_value(s)>=MOV_TRIG_TH) || (s.startsWith("occ") && parse_output_value(s)>=OCC_TRIG_TH)) s_mask |= 4;
    if(DEBUG) Serial.println(s);
  }

  // Hotspot captive portal
  if(dnsServer)
    dnsServer->processNextRequest();

  // Main logic loop
  if(is_dark_mode){ // in night
    if(is_smartlight_on){ // when light/led is on
      unsigned long ul = 0;
      if(s_mask & 1){
        ul = millis()+DELAY_ON_MOV;
        if(ul>elapse) elapse = ul;
      }
      if(s_mask & 2){
        ul = millis()+DELAY_ON_OCC;
        if(ul>elapse) elapse = ul;
      }
      if(millis()>elapse){
        smartlight_off();
        tm_smartlight_off = millis();
      }
    }else{  // when light/led is off
      if(s_mask & 4){
        if(is_smartctl())smartlight_on();
        elapse = millis()+DELAY_ON_MOV;
      }else if(ambient_level<DARK_TH_LOW && millis()-tm_smartlight_off>5000){ // return to day mode
        set_sensor(false);
        is_dark_mode = false;
      }
    }
  }else{ // in day
    if(ambient_level>DARK_TH_HIGH && is_smartctl()){
      set_sensor(true);
      is_dark_mode = true;
    }
  }
 
  delay(1);
}
