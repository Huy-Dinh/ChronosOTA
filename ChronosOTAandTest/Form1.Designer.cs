namespace ChronosOTAandTest
{
    partial class Form1
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Form1));
            this.discoveredDeviceListBox = new System.Windows.Forms.ListBox();
            this.COMPortComboBox = new System.Windows.Forms.ComboBox();
            this.openClosePortButton = new System.Windows.Forms.Button();
            this.logListBox = new System.Windows.Forms.ListBox();
            this.OTAButton = new System.Windows.Forms.Button();
            this.hexFilePathTextbox = new System.Windows.Forms.TextBox();
            this.browseButton = new System.Windows.Forms.Button();
            this.startStopScanButton = new System.Windows.Forms.Button();
            this.connectButton = new System.Windows.Forms.Button();
            this.connectionLabel = new System.Windows.Forms.Label();
            this.getDeviceInfoButton = new System.Windows.Forms.Button();
            this.gattNameLabel = new System.Windows.Forms.Label();
            this.serialNumberLabel = new System.Windows.Forms.Label();
            this.firmwareRevLabel = new System.Windows.Forms.Label();
            this.sendSerialNumberButton = new System.Windows.Forms.Button();
            this.serialNumberInputTextbox = new System.Windows.Forms.TextBox();
            this.sleepModeButton = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // discoveredDeviceListBox
            // 
            this.discoveredDeviceListBox.FormattingEnabled = true;
            this.discoveredDeviceListBox.ItemHeight = 20;
            this.discoveredDeviceListBox.Location = new System.Drawing.Point(18, 65);
            this.discoveredDeviceListBox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.discoveredDeviceListBox.Name = "discoveredDeviceListBox";
            this.discoveredDeviceListBox.Size = new System.Drawing.Size(409, 344);
            this.discoveredDeviceListBox.TabIndex = 0;
            this.discoveredDeviceListBox.SelectedIndexChanged += new System.EventHandler(this.discoveredDeviceListBox_SelectedIndexChanged);
            // 
            // COMPortComboBox
            // 
            this.COMPortComboBox.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.COMPortComboBox.FormattingEnabled = true;
            this.COMPortComboBox.Location = new System.Drawing.Point(18, 17);
            this.COMPortComboBox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.COMPortComboBox.Name = "COMPortComboBox";
            this.COMPortComboBox.Size = new System.Drawing.Size(180, 28);
            this.COMPortComboBox.TabIndex = 1;
            // 
            // openClosePortButton
            // 
            this.openClosePortButton.Location = new System.Drawing.Point(208, 14);
            this.openClosePortButton.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.openClosePortButton.Name = "openClosePortButton";
            this.openClosePortButton.Size = new System.Drawing.Size(220, 35);
            this.openClosePortButton.TabIndex = 2;
            this.openClosePortButton.Text = "Open";
            this.openClosePortButton.UseVisualStyleBackColor = true;
            this.openClosePortButton.Click += new System.EventHandler(this.openClosePortButton_Click);
            // 
            // logListBox
            // 
            this.logListBox.FormattingEnabled = true;
            this.logListBox.ItemHeight = 20;
            this.logListBox.Location = new System.Drawing.Point(18, 469);
            this.logListBox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.logListBox.Name = "logListBox";
            this.logListBox.Size = new System.Drawing.Size(934, 224);
            this.logListBox.TabIndex = 3;
            // 
            // OTAButton
            // 
            this.OTAButton.Location = new System.Drawing.Point(444, 424);
            this.OTAButton.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.OTAButton.Name = "OTAButton";
            this.OTAButton.Size = new System.Drawing.Size(508, 35);
            this.OTAButton.TabIndex = 4;
            this.OTAButton.Text = "Over-the-air Device Firmware Update";
            this.OTAButton.UseVisualStyleBackColor = true;
            this.OTAButton.Click += new System.EventHandler(this.OTAButton_Click);
            // 
            // hexFilePathTextbox
            // 
            this.hexFilePathTextbox.Location = new System.Drawing.Point(444, 383);
            this.hexFilePathTextbox.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.hexFilePathTextbox.Name = "hexFilePathTextbox";
            this.hexFilePathTextbox.ReadOnly = true;
            this.hexFilePathTextbox.Size = new System.Drawing.Size(382, 26);
            this.hexFilePathTextbox.TabIndex = 5;
            // 
            // browseButton
            // 
            this.browseButton.Location = new System.Drawing.Point(840, 379);
            this.browseButton.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.browseButton.Name = "browseButton";
            this.browseButton.Size = new System.Drawing.Size(112, 35);
            this.browseButton.TabIndex = 6;
            this.browseButton.Text = "Browse";
            this.browseButton.UseVisualStyleBackColor = true;
            this.browseButton.Click += new System.EventHandler(this.browseButton_Click);
            // 
            // startStopScanButton
            // 
            this.startStopScanButton.Location = new System.Drawing.Point(18, 419);
            this.startStopScanButton.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.startStopScanButton.Name = "startStopScanButton";
            this.startStopScanButton.Size = new System.Drawing.Size(182, 35);
            this.startStopScanButton.TabIndex = 7;
            this.startStopScanButton.Text = "Start Scan";
            this.startStopScanButton.UseMnemonic = false;
            this.startStopScanButton.UseVisualStyleBackColor = true;
            this.startStopScanButton.Click += new System.EventHandler(this.startStopScanButton_Click);
            // 
            // connectButton
            // 
            this.connectButton.Location = new System.Drawing.Point(207, 419);
            this.connectButton.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.connectButton.Name = "connectButton";
            this.connectButton.Size = new System.Drawing.Size(220, 35);
            this.connectButton.TabIndex = 8;
            this.connectButton.Text = "Connect";
            this.connectButton.UseMnemonic = false;
            this.connectButton.UseVisualStyleBackColor = true;
            this.connectButton.Click += new System.EventHandler(this.connectButton_Click);
            // 
            // connectionLabel
            // 
            this.connectionLabel.AutoSize = true;
            this.connectionLabel.Location = new System.Drawing.Point(440, 20);
            this.connectionLabel.Name = "connectionLabel";
            this.connectionLabel.Size = new System.Drawing.Size(51, 20);
            this.connectionLabel.TabIndex = 9;
            this.connectionLabel.Text = "label1";
            // 
            // getDeviceInfoButton
            // 
            this.getDeviceInfoButton.Location = new System.Drawing.Point(444, 65);
            this.getDeviceInfoButton.Name = "getDeviceInfoButton";
            this.getDeviceInfoButton.Size = new System.Drawing.Size(508, 35);
            this.getDeviceInfoButton.TabIndex = 10;
            this.getDeviceInfoButton.Text = "Get device info";
            this.getDeviceInfoButton.UseVisualStyleBackColor = true;
            this.getDeviceInfoButton.Click += new System.EventHandler(this.button1_Click);
            // 
            // gattNameLabel
            // 
            this.gattNameLabel.AutoSize = true;
            this.gattNameLabel.Location = new System.Drawing.Point(440, 107);
            this.gattNameLabel.Name = "gattNameLabel";
            this.gattNameLabel.Size = new System.Drawing.Size(103, 20);
            this.gattNameLabel.TabIndex = 11;
            this.gattNameLabel.Text = "GATT name: ";
            // 
            // serialNumberLabel
            // 
            this.serialNumberLabel.AutoSize = true;
            this.serialNumberLabel.Location = new System.Drawing.Point(440, 127);
            this.serialNumberLabel.Name = "serialNumberLabel";
            this.serialNumberLabel.Size = new System.Drawing.Size(115, 20);
            this.serialNumberLabel.TabIndex = 12;
            this.serialNumberLabel.Text = "Serial number: ";
            // 
            // firmwareRevLabel
            // 
            this.firmwareRevLabel.AutoSize = true;
            this.firmwareRevLabel.Location = new System.Drawing.Point(440, 147);
            this.firmwareRevLabel.Name = "firmwareRevLabel";
            this.firmwareRevLabel.Size = new System.Drawing.Size(135, 20);
            this.firmwareRevLabel.TabIndex = 13;
            this.firmwareRevLabel.Text = "Firmware revision:";
            // 
            // sendSerialNumberButton
            // 
            this.sendSerialNumberButton.Location = new System.Drawing.Point(581, 170);
            this.sendSerialNumberButton.Name = "sendSerialNumberButton";
            this.sendSerialNumberButton.Size = new System.Drawing.Size(371, 35);
            this.sendSerialNumberButton.TabIndex = 14;
            this.sendSerialNumberButton.Text = "Update Serial Number";
            this.sendSerialNumberButton.UseVisualStyleBackColor = true;
            this.sendSerialNumberButton.Click += new System.EventHandler(this.sendSerialNumberButton_Click);
            // 
            // serialNumberInputTextbox
            // 
            this.serialNumberInputTextbox.Location = new System.Drawing.Point(444, 174);
            this.serialNumberInputTextbox.MaxLength = 10;
            this.serialNumberInputTextbox.Name = "serialNumberInputTextbox";
            this.serialNumberInputTextbox.Size = new System.Drawing.Size(131, 26);
            this.serialNumberInputTextbox.TabIndex = 15;
            // 
            // sleepModeButton
            // 
            this.sleepModeButton.Location = new System.Drawing.Point(444, 211);
            this.sleepModeButton.Name = "sleepModeButton";
            this.sleepModeButton.Size = new System.Drawing.Size(508, 35);
            this.sleepModeButton.TabIndex = 16;
            this.sleepModeButton.Text = "Enter sleep mode";
            this.sleepModeButton.UseVisualStyleBackColor = true;
            this.sleepModeButton.Click += new System.EventHandler(this.sleepModeButton_Click);
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(9F, 20F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(968, 714);
            this.Controls.Add(this.sleepModeButton);
            this.Controls.Add(this.serialNumberInputTextbox);
            this.Controls.Add(this.sendSerialNumberButton);
            this.Controls.Add(this.firmwareRevLabel);
            this.Controls.Add(this.serialNumberLabel);
            this.Controls.Add(this.gattNameLabel);
            this.Controls.Add(this.getDeviceInfoButton);
            this.Controls.Add(this.connectionLabel);
            this.Controls.Add(this.connectButton);
            this.Controls.Add(this.startStopScanButton);
            this.Controls.Add(this.browseButton);
            this.Controls.Add(this.hexFilePathTextbox);
            this.Controls.Add(this.OTAButton);
            this.Controls.Add(this.logListBox);
            this.Controls.Add(this.openClosePortButton);
            this.Controls.Add(this.COMPortComboBox);
            this.Controls.Add(this.discoveredDeviceListBox);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.Margin = new System.Windows.Forms.Padding(4, 5, 4, 5);
            this.MaximizeBox = false;
            this.Name = "Form1";
            this.Text = "Chronos OTA and Test";
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.ListBox discoveredDeviceListBox;
        private System.Windows.Forms.ComboBox COMPortComboBox;
        private System.Windows.Forms.Button openClosePortButton;
        private System.Windows.Forms.ListBox logListBox;
        private System.Windows.Forms.Button OTAButton;
        private System.Windows.Forms.TextBox hexFilePathTextbox;
        private System.Windows.Forms.Button browseButton;
        private System.Windows.Forms.Button startStopScanButton;
        private System.Windows.Forms.Button connectButton;
        private System.Windows.Forms.Label connectionLabel;
        private System.Windows.Forms.Button getDeviceInfoButton;
        private System.Windows.Forms.Label gattNameLabel;
        private System.Windows.Forms.Label serialNumberLabel;
        private System.Windows.Forms.Label firmwareRevLabel;
        private System.Windows.Forms.Button sendSerialNumberButton;
        private System.Windows.Forms.TextBox serialNumberInputTextbox;
        private System.Windows.Forms.Button sleepModeButton;
    }

}

