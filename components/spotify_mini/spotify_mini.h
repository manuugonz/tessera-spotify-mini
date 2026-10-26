#pragma once
#include "esphome/core/component.h"
#include "esphome/components/smart_display/plugin_api.h"

namespace esphome::spotify_mini {
class PlayerCard;
class SpotifyMini : public Component, public tessera::Plugin {
 public:
  void setup() override;
  void on_message(JsonObjectConst message) override;
  float get_setup_priority() const override { return setup_priority::DATA; }
  PlayerCard *card{nullptr};  // non-owning; card clears this before the core deletes it
};
}
