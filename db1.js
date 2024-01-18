
const userSchema = new mongoose.Schema({
  name: {
    type: String,
    required: [true, "Name not provided "],
  },
  email: {
    type: String,
    lowercase: true,
    trim: true,
    required: [true, "email not provided"]
  },
  address: {
    type: String,
  },
  address_pin: {
    type: String,
  },
  mobile: {
    type: String,
    unique: [true, "Mobile already exists in database!"],
    match: /((\+*)((0[ -]*)*|((91 )*))((\d{12})+|(\d{10})+))|\d{5}([- ]*)\d{6}/,
  },
  role: {
    type: String,
    enum: ["superadmin", "stateadmin", "devicemanufacture", "dealer", "owner", "filment", "sosadmin", "teamleader", "sosexecutive"],
    required: [true, "Please specify user role"]
  },
  usertype: {
    type: String,
    default: 'main',
  },
  roleassign: {
    type: Array,
    default: ["unlockuser", "activeuser", "deactivateuser", "addsubuser", "editsubuser", "deletesubuser", "adduser", "edituser", "assinguser", "deleteuser", "adddevice", "editdevice", "deleteDevice", "addmodel", "editmodel", "deletemodel"],
  },
  parent: {
    type: String,
  },
  stateid: {
    type: String,
  },
  status: {
    type: String,
    enum: ["active", "deactive"],
  },
  dob: {
    type: String,
  },
  panfile: {
    type: String,
  },
  kyctype: {
    type: String,
  },
  kycdocnumber: {
    type: String,
  },
  kycfile: {
    type: String,
  },
  mobileotp: {
    type: String,
  },
  mobileotpsend: {
    type: String,
  },
  token: String,
  gstnnumber: {
    type: String,
  },
  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  created: {
    type: Date,
    default: Date.now
  },
  Access: {
    type: Array,
  },

});
const manufacturerSchema = new mongoose.Schema({

  company_name: {
    type: String,
    required: [true, "Name not provided "],
  },
  address: {
    type: String,
  },
  address_pin: {
    type: String,
  },
  gstnnumber: {
    type: String,
  },

  users: {
    type: Array,
    required: [true, "Atleast one user required"],
  },

  deviceModel: {
    type: Array,
  },
  retailer: {
    type: Array,
  },

  document_path: {
    type: String,
  },
  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  created: {
    type: Date,
    default: Date.now
  },

  Access: {
    type: Array,
  },
});
const retailerSchema = new mongoose.Schema({

  name: {
    type: String,
    required: [true, "Name not provided "],
  },
  address: {
    type: String,
  },
  address_pin: {
    type: String,
  },
  gstnnumber: {
    type: String,
  },
  document_path: {
    type: String,
  },

  users: {
    type: Array,
    required: [true, "Atleast one user required"],
  },
  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  created: {
    type: Date,
    default: Date.now
  },

  Access: {
    type: Array,
  },
});
const deviceSchema = new mongoose.Schema({
  deviceModel: {
    type: int,
    required: [true, "Model not provided "],
  },
  status: {
    type: String,
    enum: [Created, FactoryTestOK, ShipedtoRetailer, Sold, Installed, Active, Device error, Discontinued]
  },
  softwareLatestVersion: {
    type: String,
  },
  vehicle: {
    type: int,
    required: [true, "Vehicle not provided "],
  },
  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  created: {
    type: Date,
    default: Date.now
  },

});
const deviceModelSchema = new mongoose.Schema({
  deviceModel: {
    type: String,
    required: [true, "Model not provided "],
  },

  status: {
    type: String,
    enum: ["active", "discontinued"],
  },
  hardwareVersion: {
    type: String,
    required: [true, "Version not provided "],
  },
  softwareLatestVersion: {
    type: String,
    required: [true, "Version not provided "],
  },
  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  created: {
    type: Date,
    default: Date.now
  },
});

const fotaSchema = new mongoose.Schema({
  deviceMode: {
    type: int,
    required: [true, "Model not provided "],
  },

  status: {
    type: String,
    enum: ["active", "notactive"],
  },
  softwareVersion: {
    type: String,
    required: [true, "Version not provided "],
  },
  firmwarePath: {
    type: String,
    required: [true, "firmware path not provided "],
  },
  firmwareHex: {
    type: String,
    required: [true, "firmware hex not provided "],
  },
  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  created: {
    type: Date,
    default: Date.now
  },
});
const vehicleSchema = new mongoose.Schema({

  status: {
    type: String,
    enum: ["active", "deactive"],
  },
  access: {
    type: Array,
  },
  vregno: {
    type: String,
  },
  engineno: {
    type: String,
  },
  chessisno: {
    type: String,
  },
  vehiclemake: {
    type: String,
  },
  vehiclemodel: {
    type: String,
  },
  vehiclecategory: {
    type: String,
  },
  rcfilepath: {
    type: String,
  },
  owner: {
    type: int,
    required: [true, "Owner not provided "],
  },

  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  created: {
    type: Date,
    default: Date.now
  },
});
const trackingSchema = new mongoose.Schema({
  created: {
    type: Date,
    default: Date.now
  },
});
const trackingLogSchema = new mongoose.Schema({
  created: {
    type: Date,
    default: Date.now
  },
});
const sessionSchema = new mongoose.Schema({
  loginTime: {
    type: Date,
    default: Date.now
  },
  user: {
    type: int,
    required: [true, "user not provided "],
  },
  token: {
    type: String,
    required: [true, "token not provided "],
  },
  otp: {
    type: int,
  },
  status: {
    type: String,
    enum: ["otpsent", "login", "logout", "timeout"],
  },

});
const otpRequestSchema = new mongoose.Schema({
  otpTime: {
    type: Date,
    default: Date.now
  },
  type: {
    type: String,
    enum: ["email", "sms",],
  },
  user: {
    type: int,
    required: [true, "user not provided "],
  },
  otp: {
    type: String,
    required: [true, "otp not provided "],
  },
  status: {
    type: String,
    enum: ["otpsent", "errorsending", "verified", "donotmatch", "timeout"],
  },

});

const editRequestSchema = new mongoose.Schema({
  time: {
    type: Date,
    default: Date.now
  },
  type: {
    type: String,
    enum: ["owner", "device", "vehicle", "devicemodel", "retailer", "manufacturer",],
  },

  from_user: {
    type: int,
    required: [true, "user not provided "],
  },
  to_user: {
    type: int,
    required: [true, "user not provided "],
  },
  otp: {
    type: int,
  },
  newdataid: {
    type: int,
  },
  olddataid: {
    type: int,
  },

  status: {
    type: String,
    enum: ["requestsent", "accepted", "rejected"],
  },

});

const settingsSchema = new mongoose.Schema({

  velid_time: {
    type: Date,
    default: Date.now
  },
  type: {
    type: String,
    enum: ["......",],
  },

  createdby: {
    type: String,
    required: [true, "Creator not provided "],
  },
  settingsstring: {
    type: String,
  },
  settingsmethod: {
    type: String,
  },
  created: {
    type: Date,
    default: Date.now
  },


});



//API_list
UserManagement = [create_user, update_user, password_resset, send_email_otp, send_sms_otp, user_login, user_logout, user_get_parent, get_list, get_detailse,]
ManufacturerManagement = [create_manufacturer, update_manufacturer, add_user_to_manufacturer, add_retailer, add_devicemodel, get_list, get_detailse,]
RetailerManagement = [create_retailer, update_retailer, get_list, get_detailse,]
DevicemaodelManagement = [create_devicemodel, update_devicemodel, add_firmware, add_device_bulk, get_list, get_detailse,]
DeviceManagement = [create_device, update_device, tag_vehicle, get_list, get_detailse, get_vehicle, get_owner,]
VehicleManagement = [create_vehicle, edit_access, update_vehicle, get_list, get_detailse, get_owner,]
TrackingManagement = [get_live_tracking, get_history_tracking]


//View_list
Basic = [LoginView, PasswordRessetView, OtpView, Signup_verification]
SuperAdminDashboard = [StateAdminPanel[List, View, Edit, Create], StatisticsView, VehicleListTab[FilterPanel], MapView,]
StateAdminDashboard = [
  ManufacturerPanel[List, View, Edit, Create],
  RetailerPanel[List, View, Edit],
  DeviceModelPanel[List[filter], View],
  DevicePanel[List[filter], View, Edit],
  OwnerPanel[List[filter], Edit, View],
  VehiclePanel[List[filter], Edit, View],
  StatisticsView,
  MapView,
]
ManufacturerDashboard = [
  RetailerPanel[List, Add, View, Edit, Create],
  DeviceModelPanel[List, View, Edit, Create, addFirmware, addBulkdevicelist, asignRetailer],
  DevicePanel[List[filter], View, Edit, Create],
  OwnerPanel[List[filter], Edit, View],
  VehiclePanel[List[filter], Edit, View],
  StatisticsView,
  MapView,
  pendingRequestPanel[list, view]
]
RetailerDashboard = [
  DeviceModelPanel[List, View],
  DevicePanel[List[filter], View, UpdateSettings, Tagging, activation],
  OwnerPanel[List[filter], Add, Create, Edit, View],
  VehiclePanel[List[filter], Add, Create, Edit, View],
  StatisticsView,
  MapView,
  pendingRequestPanel[list, view]
]
VehicleOwnerDashboard = [
  ProfilePanel[view],
  VehicleListTab[list, view],
  MapView,
  pendingRequestPanel[list, view]
]


