using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Diagnostics;
using Nordicsemi;
using System.Threading;

namespace ChronosOTAandTest
{
    public partial class Form1 : Form
    {
        #region Global variables
        // Pipes for BLE communication
        int pipeNumberSerialNumber;
        int pipeNumberFirmwareRev;
        int pipeNumberGATTName;
        int pipeNumberSerialEditCCCD;
        int pipeNumberSerialAndSleepMode;

        // This doesn't change, so I'm gonna leave this here as a global const
        byte[] sleepModeCommand = { 0x02, 0x07, 0xF0, 0x55, 0xAA, 0x55, 0xAA };

        // Master Emulator
        MasterEmulator BLEMasterEmulator;

        // Background worker for responsive GUI
        BackgroundWorker initMasterEmulatorWorker = new BackgroundWorker();
        BackgroundWorker scanningWorker = new BackgroundWorker();

        // Binding sources and universal variables
        BindingSource discoveredDevicesList;
        BindingSource logList;
        List<BtDevice> listOfDevices = new List<BtDevice>();

        // File path and filters
        String batPath = "\\lib\\dfu\\dfu.bat";
        String dfuPath = "\\lib\\dfu/";
        List<string> filterStringList = new List<string>(new string[] { "F-WDP", "DfuTarg", "Chronos" });

        //boolean for resource control
        bool isConnected;
        bool isOpen;
        bool isScanning;
        #endregion

        public Form1()
        {
            InitializeComponent();
            initializeStuffs();
            initializeMasterEmulator();
            logList.Add("Starting");
            this.Cursor = Cursors.WaitCursor;
        }

        #region initializors
        private void initializeMasterEmulator()
        {
            initMasterEmulatorWorker.DoWork += OnInitMasterEmulatorWorkerDoWork;
            initMasterEmulatorWorker.RunWorkerCompleted += OnInitMasterEmulatorWorkerCompleted;
            initMasterEmulatorWorker.RunWorkerAsync();
        }

        void OnInitMasterEmulatorWorkerDoWork(object sender, DoWorkEventArgs e)
        {
            BLEMasterEmulator = new MasterEmulator();

            RegisterEventHandlers();
            IEnumerable<string> usbDevices = BLEMasterEmulator.EnumerateUsb();
            this.BeginInvoke((MethodInvoker)delegate ()
            {
                List<string> tempUSBList = new List<string>(usbDevices);
                int tempIterator = 0;
                for (tempIterator = 0; tempIterator < tempUSBList.Count; tempIterator++)
                {
                    COMPortComboBox.Items.Add(tempUSBList[tempIterator]);
                }
                if (tempUSBList.Count > 0)
                {
                    COMPortComboBox.SelectedItem = COMPortComboBox.Items[0];
                    logList.Add("Found COM port(s)");
                }
                else
                {
                    logList.Add("No COM ports found");
                }
                ScrollLogToBottom();
            });
            initMasterEmulatorWorker.DoWork -= OnInitMasterEmulatorWorkerDoWork;
        }

        void OnInitMasterEmulatorWorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            this.BeginInvoke((MethodInvoker)delegate ()
            {
                this.Cursor = Cursors.Default;
                if (e.Error != null)
                {
                    MessageBox.Show(String.Format("{0}: {1}", "Error", e.ToString()));
                }
                else
                {
                    openClosePortButton.Enabled = true;
                }
            });
            initMasterEmulatorWorker.RunWorkerCompleted -= OnInitMasterEmulatorWorkerCompleted;
        }

        private void initializeStuffs()
        {
            // Initialize binding sources and other variables
            discoveredDevicesList = new BindingSource();
            logList = new BindingSource();
            isConnected = false;
            isOpen = false;
            isScanning = false;

            // Initialize controls
            discoveredDeviceListBox.Items.Clear();
            COMPortComboBox.Items.Clear();
            openClosePortButton.Text = "Open";
            openClosePortButton.Enabled = false;
            OTAButton.Enabled = false;
            startStopScanButton.Enabled = false;
            connectButton.Enabled = false;
            connectionLabel.Text = "Disconnected";
            connectionLabel.ForeColor = Color.White;
            connectionLabel.BackColor = Color.Red;
            getDeviceInfoButton.Enabled = false;
            serialNumberInputTextbox.Enabled = false;
            sendSerialNumberButton.Enabled = false;
            sleepModeButton.Enabled = false;

            // Binding sources to controls
            discoveredDeviceListBox.DataSource = discoveredDevicesList;
            logListBox.DataSource = logList;
        }

        private void PerformPipeSetup()
        {
            const ushort serialAndFirmwareNumberServiceUUID = 0x180A;
            const ushort serialNumberCharUUID = 0x2A25;
            const ushort firmwareRevCharUUID = 0x2A26;

            const ushort gattNameServiceUUID = 0x1800;
            const ushort gattNameCharUUID = 0x2A00;

            const string serialNumberEditServiceUUID = "3DDA0001-957F-7D4A-34A6-74696673696D";
            const string serialNumberEditCharUUID = "3DDA0002-957F-7D4A-34A6-74696673696D";


            // Serial pipe
            BtUuid serviceUuid1 = new BtUuid(serialAndFirmwareNumberServiceUUID);
            PipeStore pipeStore = PipeStore.Remote;
            BLEMasterEmulator.SetupAddService(serviceUuid1, pipeStore);

            BtUuid charDefUuid1 = new BtUuid(serialNumberCharUUID);
            byte[] data = new byte[] { };
            BLEMasterEmulator.SetupAddCharacteristicDefinition(charDefUuid1, 10, data);
            pipeNumberSerialNumber = BLEMasterEmulator.SetupAssignPipe(PipeType.ReceiveRequest);

            // Firmware Rev Pipe
            BtUuid serviceUuid2 = new BtUuid(serialAndFirmwareNumberServiceUUID);
            BLEMasterEmulator.SetupAddService(serviceUuid2, PipeStore.Remote);

            BtUuid charDefUuid2 = new BtUuid(firmwareRevCharUUID);
            BLEMasterEmulator.SetupAddCharacteristicDefinition(charDefUuid2, 17, data);
            pipeNumberFirmwareRev = BLEMasterEmulator.SetupAssignPipe(PipeType.ReceiveRequest);

            // GATT name pipe
            BtUuid serviceUuid3 = new BtUuid(gattNameServiceUUID);
            BLEMasterEmulator.SetupAddService(serviceUuid3, PipeStore.Remote);

            BtUuid charDefUuid3 = new BtUuid(gattNameCharUUID);
            BLEMasterEmulator.SetupAddCharacteristicDefinition(charDefUuid3, 50, data);
            pipeNumberGATTName = BLEMasterEmulator.SetupAssignPipe(PipeType.ReceiveRequest);


            // serial edit pipe
            BtUuid serviceUuid4 = new BtUuid(serialNumberEditServiceUUID);
            BLEMasterEmulator.SetupAddService(serviceUuid4, PipeStore.Remote);

            BtUuid charDefUuid4 = new BtUuid(serialNumberEditCharUUID);
            BLEMasterEmulator.SetupAddCharacteristicDefinition(charDefUuid4, 14, data);
            pipeNumberSerialEditCCCD = BLEMasterEmulator.SetupAssignPipe(PipeType.Receive);

            // serial edit pipe send
            BtUuid serviceUuid5 = new BtUuid(serialNumberEditServiceUUID);
            BLEMasterEmulator.SetupAddService(serviceUuid5, PipeStore.Remote);

            BtUuid charDefUuid5 = new BtUuid(serialNumberEditCharUUID);
            BLEMasterEmulator.SetupAddCharacteristicDefinition(charDefUuid5, 14, data);
            pipeNumberSerialAndSleepMode = BLEMasterEmulator.SetupAssignPipe(PipeType.TransmitWithAck);
        }
        #endregion

        #region BLEEventHandlers
        void OnLogMessage(object sender, ValueEventArgs<string> e)
        {
            this.BeginInvoke((MethodInvoker)delegate ()
            {
                logList.Add((String)e.Value.ToString());
                if (e.Value.ToString() == "Open")
                {
                    isOpen = true;
                    openClosePortButton.Text = "Close";
                    startStopScanButton.Enabled = true;
                }
                else if (e.Value.ToString() == "Close")
                {
                    isOpen = false;
                    openClosePortButton.Text = "Open";
                    startStopScanButton.Enabled = false;
                    connectButton.Enabled = false;
                    if (discoveredDeviceListBox.SelectedItems.Count > 0)
                    {
                        OTAButton.Enabled = true;
                    }
                    isConnected = false;
                    isScanning = false;
                    startStopScanButton.Text = "Start scanning";
                    connectButton.Text = "Connect";
                }
                ScrollLogToBottom();
            });
        }

        void OnDataReceived(object sender, PipeDataEventArgs e)
        {
            if (e.PipeNumber == pipeNumberSerialEditCCCD)
            {

            }
        }

        void OnConnected(object sender, EventArgs e)
        {
            this.BeginInvoke((MethodInvoker)delegate ()
            {
                connectButton.Text = "Disconnect";
                isConnected = true;
                logList.Add("Connected: " + e.ToString());
                ScrollLogToBottom();

                connectionLabel.Text = "Connected";
                connectionLabel.BackColor = Color.Green;

                getDeviceInfoButton.Enabled = true;
                serialNumberInputTextbox.Enabled = true;
                sendSerialNumberButton.Enabled = true;
                sleepModeButton.Enabled = true;
            });
        }

        void OnDisconnected(object sender, ValueEventArgs<DisconnectReason> e)
        {
            this.BeginInvoke((MethodInvoker)delegate ()
            {
                isConnected = false;
                connectButton.Text = "Connect";
                logList.Add("Disconnected: " + e.Value.ToString());
                ScrollLogToBottom();

                connectionLabel.Text = "Disconnected";
                connectionLabel.BackColor = Color.Red;

                getDeviceInfoButton.Enabled = false;
                serialNumberInputTextbox.Enabled = false;
                sendSerialNumberButton.Enabled = false;
                sleepModeButton.Enabled = false;
            });
        }

        private void OnConnectionUpdateRequest(object sender, ConnectionUpdateRequestEventArgs e)
        {
            BLEMasterEmulator.SendConnectionUpdateResponse(e.Identifier, ConnectionUpdateResponse.Accepted);
            BtConnectionParameters cxParam = new BtConnectionParameters();
            cxParam.ConnectionIntervalMs = e.ConnectionIntervalMinMs;
            cxParam.SupervisionTimeoutMs = e.ConnectionSupervisionTimeoutMs;
            BLEMasterEmulator.UpdateConnectionParameters(cxParam);
        }

        private void BLEMasterEmulator_DeviceDiscovered(object sender, ValueEventArgs<BtDevice> e)
        {
            this.BeginInvoke((MethodInvoker)delegate ()
            {
                for (int i = 0; i < listOfDevices.Count; i++)
                {
                    if (listOfDevices[i].DeviceAddress == e.Value.DeviceAddress)
                    {
                        listOfDevices.RemoveAt(i);
                    }
                }
                listOfDevices.Add(e.Value);
                listOfDevices = listOfDevices.OrderByDescending(o => Int32.Parse(o.DeviceInfo[DeviceInfoType.Rssi])).ToList();
                discoveredDevicesList.Clear();

                int limit = 0;
                if (listOfDevices.Count > 28)
                {
                    limit = listOfDevices.Count;
                }
                else
                {
                    limit = listOfDevices.Count;
                }
                for (int i = 0; i < limit; i++)
                {
                    string deviceName = "";
                    IDictionary<DeviceInfoType, string> deviceInfo = listOfDevices[i].DeviceInfo;
                    if (deviceInfo.ContainsKey(DeviceInfoType.CompleteLocalName))
                    {
                        deviceName = "(" + deviceInfo[DeviceInfoType.Rssi].ToString() + ") " +
                            deviceInfo[DeviceInfoType.CompleteLocalName] + " - " + listOfDevices[i].DeviceAddress.Value;
                        if (matchFilter(deviceInfo[DeviceInfoType.CompleteLocalName]))
                        {
                            discoveredDevicesList.Add(deviceName);
                        }
                    }
                    else if (deviceInfo.ContainsKey(DeviceInfoType.ShortenedLocalName))
                    {
                        deviceName = "(" + deviceInfo[DeviceInfoType.Rssi].ToString() + ") " +
                            deviceInfo[DeviceInfoType.ShortenedLocalName] + " - " + listOfDevices[i].DeviceAddress.Value;
                        if (matchFilter(deviceInfo[DeviceInfoType.ShortenedLocalName]))
                        {
                            discoveredDevicesList.Add(deviceName);
                        }
                    }
                    else
                    {
                        deviceName = "(" + deviceInfo[DeviceInfoType.Rssi].ToString() + ") " +
                            listOfDevices[i].DeviceAddress.Value;
                    }
                }
                discoveredDevicesList.ResetBindings(false);
            });
        }
        #endregion

        #region Miscellaneous
        private void RegisterEventHandlers()
        {
            BLEMasterEmulator.LogMessage += OnLogMessage;
            BLEMasterEmulator.DataReceived += OnDataReceived;
            BLEMasterEmulator.Connected += OnConnected;
            BLEMasterEmulator.Disconnected += OnDisconnected;
            BLEMasterEmulator.ConnectionUpdateRequest += OnConnectionUpdateRequest;
            BLEMasterEmulator.DeviceDiscovered += BLEMasterEmulator_DeviceDiscovered;
        }

        void ScrollLogToBottom()
        {
            if (InvokeRequired)
            {
                this.Invoke((Action)delegate
                {
                    ScrollLogToBottom();
                });
                return;
            }
            int visibleItems = logListBox.ClientSize.Height / logListBox.ItemHeight;
            logListBox.TopIndex = Math.Max(logListBox.Items.Count - visibleItems + 1, 0);
        }

        bool matchFilter(string inputString)
        {
            int i = 0;
            for (i = 0; i < filterStringList.Count; i++)
            {
                if (inputString == filterStringList[i])
                {
                    return true;
                }
            }
            return false;
        }
        #endregion

        #region controlEventHandlers
        private void openClosePortButton_Click(object sender, EventArgs e)
        {
            int selectedItem = COMPortComboBox.SelectedIndex;
            string usbSerial;
            if (selectedItem >= 0)
            {
                usbSerial = (string)COMPortComboBox.Items[selectedItem];
            }
            else
            {
                MessageBox.Show("No device selected");
                return;
            }

            try
            {
                this.Cursor = Cursors.WaitCursor;
                if (!isOpen)
                {
                    BLEMasterEmulator.Open(usbSerial.Substring(0, usbSerial.IndexOf(" ")));
                    Thread.Sleep(500);
                    BLEMasterEmulator.Reset();
                    PerformPipeSetup();
                    Thread.Sleep(500);
                    BLEMasterEmulator.Run();
                    isOpen = true;
                }
                else
                {
                    if (BLEMasterEmulator.IsDeviceDiscoveryOngoing)
                    {
                        BLEMasterEmulator.StopDeviceDiscovery();
                    }
                    if (BLEMasterEmulator.IsConnected)
                    {
                        BLEMasterEmulator.Disconnect();
                    }
                    BLEMasterEmulator.Close();
                }
            }
            catch (Exception ex)
            {
                this.BeginInvoke((MethodInvoker)delegate ()
                {
                    MessageBox.Show("Error: " + ex.ToString());
                });
            }
            finally
            {
                this.Cursor = Cursors.Default;
            }
        }

        private void startStopScanButton_Click(object sender, EventArgs e)
        {
            BtScanParameters scanParameter = new BtScanParameters();
            scanParameter.ScanWindowMs = 50;
            scanParameter.ScanIntervalMs = 50;
            scanParameter.ScanType = BtScanType.ActiveScanning;

            if (!isScanning)
            {
                listOfDevices.Clear();
                bool check = BLEMasterEmulator.StartDeviceDiscovery(scanParameter);
                if (check)
                {
                    isScanning = true;
                    startStopScanButton.Text = "Stop scan";
                }
                else
                {
                    logList.Add("Cannot start scanning, please close and open the port again");
                    logList.Add("If that doesn't work, disconnect and reconnect the dongle then restart the application");
                    ScrollLogToBottom();
                }
                connectButton.Enabled = false;
            }
            else
            {
                BLEMasterEmulator.StopDeviceDiscovery();
                isScanning = false;
                startStopScanButton.Text = "Start scan";
                connectButton.Enabled = true;
            }
        }

        private void discoveredDeviceListBox_SelectedIndexChanged(object sender, EventArgs e)
        {
            if ((discoveredDeviceListBox.SelectedItems.Count > 0) && (!isScanning))
            {
                OTAButton.Enabled = true;
                connectButton.Enabled = true;
            }
        }

        private void browseButton_Click(object sender, EventArgs e)
        {
            OpenFileDialog zipFileOpenDialog = new OpenFileDialog();
            if (zipFileOpenDialog.ShowDialog() == DialogResult.OK)
            {
                hexFilePathTextbox.Text = zipFileOpenDialog.FileName;
            }
            zipFileOpenDialog.Dispose();
        }

        private void OTAButton_Click(object sender, EventArgs e)
        {
            string targetAddress = discoveredDeviceListBox.SelectedItem.ToString();
            targetAddress = targetAddress.Substring(targetAddress.Length - 12);

            if (File.Exists(Directory.GetCurrentDirectory().ToString() + batPath))
            {
                File.Delete(Directory.GetCurrentDirectory().ToString() + batPath);
            }
            if (isConnected)
            {
                BLEMasterEmulator.Disconnect();
            }
            if (isScanning)
            {
                BLEMasterEmulator.StopDeviceDiscovery();
                isScanning = false;
            }
            if (isOpen)
            {
                BLEMasterEmulator.Close();
            }

            StreamWriter batFileWriter = new StreamWriter(Directory.GetCurrentDirectory().ToString() + batPath);
            batFileWriter.WriteLine("cd " + "\"" + Directory.GetCurrentDirectory().ToString() + dfuPath + "\"");
            batFileWriter.WriteLine("ipy main.py --file " + "\"" + hexFilePathTextbox.Text + "\"" + " --address " + targetAddress);
            batFileWriter.WriteLine("pause");
            batFileWriter.Close();
            batFileWriter.Dispose();
            Process p = new Process();
            p.StartInfo.FileName = Directory.GetCurrentDirectory().ToString() + batPath;
            p.Start();
            p.WaitForExit();

        }

        private void connectButton_Click(object sender, EventArgs e)
        {
            if (!isConnected)
            {
                string targetAddress = discoveredDeviceListBox.SelectedItem.ToString();
                targetAddress = targetAddress.Substring(targetAddress.Length - 12);
                BtDeviceAddress ConnectTargetAddress = new BtDeviceAddress(targetAddress);
                if (BLEMasterEmulator.Connect(ConnectTargetAddress))
                {
                    // This was added due to rare problems where the peer device 
                    // initiate disconnection just after a connection is established. 
                    if ((BLEMasterEmulator.IsConnected) && BLEMasterEmulator.DiscoverPipes())
                    {
                        BLEMasterEmulator.OpenAllRemotePipes();
                    }
                }
            }
            else
            {
                // This was added due to rare problems where the peer device 
                // initiate disconnection just after a connection is established.
                try
                {
                    BLEMasterEmulator.Disconnect();
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Error: " + ex.ToString());
                }
            }
        }

        private void button1_Click(object sender, EventArgs e)
        {
            try
            {
                byte[] received = BLEMasterEmulator.RequestData(pipeNumberSerialNumber);
                string dummyString = "Serial number: " + System.Text.Encoding.ASCII.GetString(received);
                serialNumberLabel.Text = dummyString;

                received = BLEMasterEmulator.RequestData(pipeNumberFirmwareRev);
                dummyString = "Firmware revision: " + System.Text.Encoding.ASCII.GetString(received);
                firmwareRevLabel.Text = dummyString;

                received = BLEMasterEmulator.RequestData(pipeNumberGATTName);
                dummyString = "GATT name: " + System.Text.Encoding.ASCII.GetString(received);
                gattNameLabel.Text = dummyString;
            }
            catch (Exception exc)
            {
                MessageBox.Show("Error: " + exc.ToString());
            }
        }

        private void sendSerialNumberButton_Click(object sender, EventArgs e)
        {
            byte[] fullCommand = { 0x02, 0x07, 0x01, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 0 };
            byte[] input = Encoding.ASCII.GetBytes(serialNumberInputTextbox.Text);
            if (input.Length < 10)
            {
                MessageBox.Show("Please input a serial number of 10 characters");
            }
            else
            {
                for (int i = 0; i < 10; i++)
                {
                    fullCommand[i + 3] = input[i];
                }
                if (BLEMasterEmulator.SendData(pipeNumberSerialAndSleepMode, fullCommand))
                {
                    Thread.Sleep(400);
                    byte[] received = BLEMasterEmulator.RequestData(pipeNumberSerialNumber);
                    string dummyString = "Serial number: " + System.Text.Encoding.ASCII.GetString(received);
                    serialNumberLabel.Text = dummyString;
                }
                else
                {
                    logList.Add("Serial edit command failed to be sent");
                }
            }
        }
        #endregion

        #region systemEventOverride
        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            BLEMasterEmulator.StopDeviceDiscovery();
            if (BLEMasterEmulator.IsConnected) BLEMasterEmulator.Disconnect();
            base.OnFormClosing(e);
        }
        #endregion

        #region testing functions
        private void sleepModeButton_Click(object sender, EventArgs e)
        {
            if (BLEMasterEmulator.SendData(pipeNumberSerialAndSleepMode, sleepModeCommand))
            {
                logList.Add("Sleep mode command sent successfully");
            }
            else
            {
                logList.Add("Sleep mode command failed to be sent");
            }
        }
        #endregion
    }
}
