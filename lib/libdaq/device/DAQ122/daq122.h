﻿#ifndef DAQ122_H
#define DAQ122_H

#include "device/base_device.h"

namespace libdaq {
namespace device {

class DAQ122 : public BaseDevice {
public:
    DAQ122();
    ~DAQ122() override;

    bool ConnectedDevice() override;
    bool UseUSBBackend() override;
    bool InitializeDevice() override;
    bool ConfigureADCParameters(DAQADCSampleRate sample_rate, DAQVoltage voltage) override;
    bool ConfigADCChannel(uint8_t channel) override;
    bool StartADCCollection() override;
    bool StopADCCollection() override;

protected:
    bool ReceiveData(int timeout) override;
    bool ParseData(const unique_ptr<uint8_t> &raw_data_buffer, int raw_data_size) override;

    bool SendConnected() override;
    bool SendStartCollection() override;
    bool SendStopCollection() override;
    bool InitADCChannel();

private:
    std::vector<uint8_t> daq122_send_packet_header_ = {0x4C, 0x52, 0xAA, 0x55};
    std::vector<uint8_t> daq122_send_packet_tail_ = {0xAA, 0x55, 0x55, 0xAA};
    std::vector<uint8_t> BuildSendPacket(uint16_t command, const std::vector<uint8_t>& data);
    bool SendCommand(uint16_t command, const std::vector<uint8_t>& data) override;
    bool SendConfigureCommand();
};

} // namespace device
} // namespace libdaq

#endif // DAQ122_H
