#include "spotify_mini.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <string>

namespace esphome::spotify_mini {
namespace ui = tessera::ui;
using tessera::Font;
using tessera::Text;

static std::string cover(const Text &id) {
  if (id.size() != 40) return "";
  for (char c : id) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return "";
  return std::string("https://i.scdn.co/image/") + id.c_str();
}
static void visible(lv_obj_t *o, bool show) {
  if (!o) return;
  if (show) lv_obj_remove_flag(o, LV_OBJ_FLAG_HIDDEN);
  else lv_obj_add_flag(o, LV_OBJ_FLAG_HIDDEN);
}
static lv_obj_t *label(lv_obj_t *parent, int x, int y, int w, Font font = Font::BODY) {
  auto *o = ui::label(parent, font, theme::INK);
  lv_obj_set_pos(o, x, y);
  lv_obj_set_width(o, std::max(1, w));
  return o;
}
static void icon(lv_obj_t *o, uint32_t point) { ui::set_text(o, ui::icon(point)); }

struct Now {
  Text title, artist, image, state, error, device;
  float position{0}, duration{0};
  uint32_t at{0};
  void read(JsonObjectConst d) {
    JsonObjectConst a = d["attributes"];
    title = a["media_title"] | "";
    artist = a["media_artist"] | "";
    image = a["mini_cover"] | "";
    state = d["state"] | "";
    error = a["mini_error"] | "";
    device = a["mini_device"] | "";
    position = a["media_position"] | 0.0f;
    duration = a["media_duration"] | 0.0f;
    at = a["mini_position_at"] | 0u;
  }
  const char *status(const SpotifyMini *p) const {
    if (!error.empty()) {
      const char *s = p->text(error.c_str());
      return *s ? s : p->text("failed");
    }
    return p->text(state.empty() ? "choose" : state.c_str());
  }
};

class PlayerTile : public tessera::Tile {
 public:
  explicit PlayerTile(SpotifyMini *p) : p_(p) {}
  void create(const tessera::TileContext &c) override {
    entity_ = c.entity;
    tile_ = c.tile;
    w_ = c.width; h_ = c.height;
    const int pad = std::max(ui::px(6), ui::mm(2));
    const int gap = ui::px(8);
    cover_only_ = w_ * 2 < h_ * 3;
    int side = cover_only_ ? std::min(w_ - 2 * pad, h_ - 2 * pad)
                           : std::min(h_ - 2 * pad, w_ * 42 / 100);
    side = std::max(1, side);
    int art_x = cover_only_ ? (w_ - side) / 2 : pad;
    int art_y = (h_ - side) / 2;
    artwork_ = ui::pictures() ? ui::picture(c.parent) : ui::block(c.parent, theme::TRACK);
    lv_obj_set_pos(artwork_, art_x, art_y);
    lv_obj_set_size(artwork_, side, side);
    lv_obj_set_style_radius(artwork_, ui::px(16), 0);
    picture_ = ui::pictures() ? artwork_ : nullptr;
    placeholder_ = label(artwork_, ui::px(4), (side - ui::line_height(Font::BODY)) / 2,
                         side - ui::px(8));
    lv_obj_set_style_text_align(placeholder_, LV_TEXT_ALIGN_CENTER, 0);
    if (!cover_only_) {
      int right = art_x + side + gap;
      int width = std::max(1, w_ - right - pad);
      int control_h = std::min(std::max(ui::mm(8), ui::line_height(Font::ICON)), h_ / 3);
      Font control_font = width / 3 < ui::line_height(Font::ICON) ? Font::ICON_SMALL : Font::ICON;
      int title_h = ui::line_height(h_ >= ui::mm(35) ? Font::TITLE : Font::BODY);
      int artist_h = ui::line_height(Font::BODY);
      int status_h = ui::line_height(Font::BODY);
      int group_h = control_h + gap + title_h + artist_h + status_h;
      int control_y = std::max(pad, (h_ - group_h) / 2);
      for (int i = 0; i < 3; ++i) {
        int x = right + width * i / 3;
        int next = right + width * (i + 1) / 3;
        hits_[i] = {x, control_y, next - x, control_h};
        keys_[i] = label(c.parent, x, control_y + (control_h - ui::line_height(control_font)) / 2,
                         next - x, control_font);
        lv_obj_set_style_text_align(keys_[i], LV_TEXT_ALIGN_CENTER, 0);
      }
      icon(keys_[0], 0xF04AE); icon(keys_[1], 0xF040A); icon(keys_[2], 0xF04AD);
      int meta_y = control_y + control_h + gap;
      title_ = label(c.parent, right, meta_y, width, h_ >= ui::mm(35) ? Font::TITLE : Font::BODY);
      artist_ = label(c.parent, right, meta_y + title_h, width);
      status_ = label(c.parent, right, meta_y + title_h + artist_h, width);
    }
    on_theme();
  }
  void on_state(JsonObjectConst d) override {
    now_.read(d);
    visible(placeholder_, !picture_ || now_.image.empty());
    ui::set_text(placeholder_, now_.error.empty() ? p_->text("ready") : now_.status(p_));
    if (title_) {
      ui::set_text(title_, now_.title.empty() ? p_->text("ready") : now_.title.c_str());
      ui::set_text(artist_, now_.artist.c_str());
      ui::set_text(status_, !now_.error.empty() ? now_.status(p_) :
                   !now_.device.empty() ? now_.device.c_str() :
                   now_.state == "paused" ? p_->text("paused") : "");
      icon(keys_[1], now_.state == "playing" ? 0xF03E4 : 0xF040A);
    }
    if (picture_) ui::set_picture(picture_, cover(now_.image), tessera::Fit::CONTAIN);
  }
  void on_theme() override {
    ui::set_fill(artwork_, tessera::Tone::NORMAL, theme::TRACK);
    ui::set_color(placeholder_, theme::INK_SOFT);
    if (title_) {
      ui::set_color(title_, theme::INK); ui::set_color(artist_, theme::INK_SOFT);
      ui::set_color(status_, theme::MUTED);
      for (auto *o : keys_) ui::set_color(o, theme::INK);
    }
  }
  void on_tap() override {
    auto at = tessera::tap_point();
    if (!cover_only_ && !entity_.empty()) {
      for (int i = 0; i < 3; ++i) {
        auto &r = hits_[i];
        if (at.x < r.x || at.x >= r.x + r.w || at.y < r.y || at.y >= r.y + r.h) continue;
        if (i == 0) tessera::action("media_player.media_previous_track", entity_.c_str());
        if (i == 1) tessera::action("media_player.media_play_pause", entity_.c_str());
        if (i == 2) tessera::action("media_player.media_next_track", entity_.c_str());
        return;
      }
    }
    tessera::open_card(p_->plugin_id(), "player", entity_.c_str(), tile_);
  }
 private:
  struct Hit { int x{}, y{}, w{}, h{}; };
  SpotifyMini *p_;
  Text entity_;
  Now now_;
  int tile_{-1}, w_{0}, h_{0};
  bool cover_only_{false};
  Hit hits_[3]{};
  lv_obj_t *artwork_{}, *picture_{}, *placeholder_{}, *title_{}, *artist_{}, *status_{}, *keys_[3]{};
};

struct Key {
  lv_obj_t *box{}, *text{};
  int x{}, y{}, w{}, h{}, action{};
};
struct Item { Text uri, title, artist, image, kind; };

class PlayerCard : public tessera::Card {
 public:
  explicit PlayerCard(SpotifyMini *p) : p_(p) { p_->card = this; }
  ~PlayerCard() override { if (p_->card == this) p_->card = nullptr; }
  void open(const tessera::CardContext &c) override {
    parent_ = c.parent; entity_ = c.entity; w_ = c.width; h_ = c.height;
    line_ = ui::line_height(Font::BODY); gap_ = ui::px(4);
    row_ = std::max(ui::mm(8), line_ + gap_);
    for (auto &k : keys_) {
      k.box = ui::block(c.parent, theme::TRACK);
      k.text = label(k.box, 0, 0, 1);
      lv_obj_set_style_text_align(k.text, LV_TEXT_ALIGN_CENTER, 0);
    }
    for (auto &o : words_) o = label(c.parent, 0, 0, w_);
    for (auto &bar : menu_bars_) {
      bar = ui::block(c.parent, theme::INK);
      lv_obj_set_style_radius(bar, LV_RADIUS_CIRCLE, 0);
    }
    art_placeholder_ = ui::block(c.parent, theme::TRACK);
    lv_obj_set_style_radius(art_placeholder_, ui::px(18), 0);
    art_label_ = label(art_placeholder_, 0, 0, 1, Font::TITLE);
    lv_obj_set_style_text_align(art_label_, LV_TEXT_ALIGN_CENTER, 0);
    if (ui::pictures()) for (auto &o : pictures_) o = ui::picture(c.parent);
    progress_track_ = ui::block(c.parent, theme::TRACK);
    progress_ = ui::block(c.parent, theme::ACCENT);
    lv_obj_set_style_radius(progress_track_, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_radius(progress_, LV_RADIUS_CIRCLE, 0);
    paint();
  }
  void on_state(JsonObjectConst data) override { now_.read(data); paint(); }
  void on_theme() override { paint(); }
  void on_tick(uint32_t epoch) override {
    if (asked_ && esphome::millis() - asked_at_ > 20000) {
      asked_ = 0; message_ = p_->text("timeout"); paint();
    }
    if (view_ != 0 || now_.duration <= 0) return;
    float pos = now_.position;
    if (now_.state == "playing" && now_.at && epoch > now_.at) pos += epoch - now_.at;
    int width = std::max(1, int(progress_width_ * std::clamp(pos / now_.duration, 0.0f, 1.0f)));
    lv_obj_set_size(progress_, width, std::max(1, ui::px(3)));
  }
  bool on_back() override {
    if (view_ != 0) {
      view_ = view_ == 2 || view_ == 3 || view_ == 5 ? 1 : 0;
      asked_ = 0; message_.clear(); paint(); return true;
    }
    return false;
  }
  void on_tap() override {
    auto p = tessera::tap_point();
    for (int i = 0; i < used_; ++i) {
      auto &k = keys_[i];
      if (p.x >= k.x && p.x < k.x + k.w && p.y >= k.y && p.y < k.y + k.h) {
        act(k.action); return;
      }
    }
  }
  void answer(JsonObjectConst m) {
    if (!asked_ || (m["re"] | 0u) != asked_) return;
    asked_ = 0;
    JsonObjectConst result = m["result"];
    const char *error = result["error"] | "";
    if (!(m["ok"] | false) || *error) {
      const char *word = p_->text(*error ? error : "failed");
      message_ = *word ? word : p_->text("failed"); paint(); return;
    }
    message_.clear();
    if (command_) { view_ = 0; paint(); return; }
    count_ = 0;
    recent_count_ = 0; recommend_count_ = 0;
    auto read_items = [&](JsonArrayConst source, int limit) {
      for (JsonObjectConst item : source) {
        if (count_ >= limit) break;
        auto &i = items_[count_++];
        i.uri = item["uri"] | ""; i.title = item["title"] | "";
        i.artist = item["artist"] | ""; i.image = item["cover"] | "";
        i.kind = item["kind"] | "";
      }
    };
    if (view_ == 1) {
      read_items(result["recent"].as<JsonArrayConst>(), 2);
      recent_count_ = count_;
      read_items(result["recommended"].as<JsonArrayConst>(), 4);
      recommend_count_ = count_ - recent_count_;
    } else read_items(result["items"].as<JsonArrayConst>(), 3);
    more_ = result["more"] | false;
    if (!count_ && view_ != 1) message_ = p_->text("empty");
    paint();
  }
 private:
  void word(int n, const char *text, int x, int y, int width) {
    auto *o = words_[n]; visible(o, true);
    lv_obj_set_pos(o, x, y); lv_obj_set_width(o, std::max(1, width));
    ui::set_color(o, theme::INK); ui::set_text(o, text);
  }
  void key(int x, int y, int w, int h, const char *text, int action, uint32_t glyph = 0) {
    if (used_ >= 48) return;
    Key &k = keys_[used_++];
    k.x = x; k.y = y; k.w = w; k.h = h; k.action = action;
    visible(k.box, true); visible(k.text, true);
    lv_obj_set_pos(k.box, x, y); lv_obj_set_size(k.box, std::max(1,w-gap_), std::max(1,h-gap_));
    bool nav = action >= 1 && action <= 4;
    bool transport = action >= 10 && action <= 12;
    theme::Role fill = action == 11 ? theme::INK :
                       nav || transport ? theme::CARD : action >= 30 && action < 34 ? theme::PAGE_SOFT : theme::TRACK;
    ui::set_fill(k.box, tessera::Tone::NORMAL, fill);
    lv_obj_set_style_bg_opa(k.box, transport && action != 11 ? LV_OPA_TRANSP : LV_OPA_COVER, 0);
    lv_obj_set_style_radius(k.box, nav ? ui::px(12) : transport ? LV_RADIUS_CIRCLE : ui::px(14), 0);
    Font face = glyph ? (transport ? Font::ICON : Font::ICON_SMALL) : Font::BODY;
    ui::set_font(k.text, face);
    ui::set_color(k.text, action == 11 ? theme::CARD : theme::INK);
    int lh = ui::line_height(face);
    lv_obj_set_pos(k.text, gap_, std::max(0,(h-gap_-lh)/2));
    lv_obj_set_width(k.text, std::max(1,w-gap_*3));
    if (glyph) icon(k.text, glyph); else ui::set_text(k.text, text);
  }
  void picture(int n, const Text &id, int x, int y, int side) {
    if (!pictures_[n] || side < 1) return;
    visible(pictures_[n], true); lv_obj_set_pos(pictures_[n], x, y);
    lv_obj_set_size(pictures_[n], side, side);
    ui::set_picture(pictures_[n], cover(id), tessera::Fit::CONTAIN);
  }
  void menu_item(int index, int word_index, int y, int height) {
    key(gap_,y,w_-gap_*2,height,"",30+index);
    auto *box = keys_[used_-1].box;
    lv_obj_set_parent(words_[word_index],box);
    lv_obj_set_parent(words_[word_index+1],box);
    int side = std::max(0,std::min(height-gap_*2,w_/7));
    bool art = pictures_[index] && !items_[index].image.empty() && side >= ui::mm(7);
    if (art) picture(index,items_[index].image,gap_*2,y+(height-side)/2,side);
    int left = art ? side+gap_*2 : gap_*2;
    int text_y = std::max(gap_,(height-line_*2)/2);
    word(word_index,items_[index].title.c_str(),left,text_y,w_-left-gap_*2);
    if(height >= line_*2+gap_*2) {
      word(word_index+1,items_[index].artist.c_str(),left,text_y+line_,w_-left-gap_*2);
      ui::set_color(words_[word_index+1],theme::INK_SOFT);
    }
  }
  void paint() {
    if (!words_[0]) return;
    for (auto &k : keys_) { visible(k.box, false); visible(k.text, false); }
    for (auto *o : words_) { visible(o, false); lv_obj_set_parent(o, parent_); ui::set_font(o, Font::BODY); }
    for (auto *o : pictures_) visible(o, false);
    for (auto *o : menu_bars_) visible(o, false);
    visible(art_placeholder_, false); visible(art_label_, false);
    visible(progress_track_, false); visible(progress_, false); used_ = 0;
    int header_w = std::max(row_ + gap_, ui::mm(13));
    if (view_ == 0) {
      key(0,0,header_w,row_,"",1,0xF0118);
      key(w_-header_w,0,header_w,row_,"",2);
      int bar_w = std::max(ui::px(12), header_w / 3);
      int bar_h = std::max(1,ui::px(2));
      for (int i=0;i<3;++i) {
        auto *bar = menu_bars_[i]; visible(bar,true);
        lv_obj_set_pos(bar,w_-header_w+(header_w-bar_w)/2,
                       (row_-gap_)/2+(i-1)*ui::px(5));
        lv_obj_set_size(bar,bar_w,bar_h);
        ui::set_fill(bar,tessera::Tone::NORMAL,theme::INK);
      }
    }
    int y = view_ == 0 ? row_ + gap_ : gap_;
    const char *status = asked_ ? p_->text("loading") : !message_.empty() ? message_.c_str() :
                         view_ == 0 && !now_.error.empty() ? now_.status(p_) : "";
    if (*status) {
      word(0,status,view_==0?header_w+gap_:gap_,view_==0?(row_-line_)/2:y,
           view_==0?std::max(1,w_-header_w*2-gap_*2):w_-gap_*2);
      ui::set_color(words_[0],theme::MUTED);
      if (view_ != 0) y += line_+gap_;
    }
    if (view_ == 0) {
      int pad = ui::px(12), art_x, art_y, side, text_x, text_y, text_w, controls_y, controls_x, controls_w;
      bool compact = h_ < row_ * 4 + line_ * 3 + gap_ * 4;
      bool wide = w_ * 5 >= h_ * 6;
      int title_h = ui::line_height(wide && !compact ? Font::HEADLINE : Font::TITLE);
      int artist_h = ui::line_height(compact ? Font::BODY : Font::BODY_LARGE);
      if (compact) {
        visible(words_[0], false);
        y = row_ + gap_;
        pad = ui::px(6);
        side = std::max(1, std::min(w_ * 42 / 100, h_ - y - pad * 2));
        art_x = pad; art_y = y + std::max(0, (h_ - y - side) / 2);
        text_x = art_x + side + pad * 2; text_w = std::max(1, w_ - text_x - pad);
        text_y = y + pad;
        controls_y = h_ - row_ - pad;
        controls_x = text_x; controls_w = text_w;
      } else if (wide) {
        side = std::max(1, std::min((w_ - pad * 4) * 52 / 100, h_ - y - pad * 2));
        art_x = pad; art_y = y + std::max(0, (h_ - y - side) / 2);
        text_x = art_x + side + pad * 2; text_w = std::max(1, w_ - text_x - pad);
        int stack = title_h + artist_h + gap_ * 5 + row_ + ui::mm(6);
        text_y = y + std::max(0, (h_ - y - stack) / 2);
        controls_y = text_y + title_h + artist_h + gap_ * 5 + ui::mm(6);
        controls_w = std::min(text_w, std::max(row_ * 5, ui::mm(60)));
        controls_x = text_x + (text_w - controls_w) / 2;
      } else {
        int reserved = title_h + artist_h + row_ + gap_ * 4 + ui::px(18);
        side = std::max(1, std::min(w_ * 70 / 100, h_ - y - reserved));
        art_x = (w_ - side) / 2; art_y = y;
        text_x = pad; text_w = std::max(1, w_ - pad * 2);
        text_y = art_y + side + gap_;
        controls_y = h_ - row_ - gap_;
        controls_w = std::min(text_w, std::max(row_ * 5, ui::mm(60)));
        controls_x = (w_ - controls_w) / 2;
      }
      visible(art_placeholder_, true);
      lv_obj_set_pos(art_placeholder_, art_x, art_y);
      lv_obj_set_size(art_placeholder_, side, side);
      ui::set_fill(art_placeholder_, tessera::Tone::NORMAL, theme::TRACK);
      visible(art_label_, !pictures_[0] || now_.image.empty());
      lv_obj_set_pos(art_label_, ui::px(6), (side - ui::line_height(Font::TITLE)) / 2);
      lv_obj_set_width(art_label_, std::max(1, side - ui::px(12)));
      ui::set_color(art_label_, theme::INK_SOFT);
      ui::set_text(art_label_, p_->text("ready"));
      if (pictures_[0] && side >= ui::mm(8) && !now_.image.empty()) {
        picture(0, now_.image, art_x, art_y, side);
        lv_obj_set_style_radius(pictures_[0], ui::px(18), 0);
      }
      ui::set_font(words_[1], wide && !compact ? Font::HEADLINE : Font::TITLE);
      ui::set_font(words_[2], compact ? Font::BODY : Font::BODY_LARGE);
      word(1,now_.title.empty()?p_->text("ready"):now_.title.c_str(),text_x,text_y,text_w);
      word(2,compact && (!now_.error.empty() || now_.state == "unavailable") ?
               now_.status(p_) : now_.artist.c_str(),text_x,text_y+title_h+gap_,text_w);
      ui::set_color(words_[2], theme::INK_SOFT);
      int progress_y = controls_y - ui::px(18);
      int progress_x = text_x;
      progress_width_ = text_w;
      if (now_.duration > 0) {
        visible(progress_track_, true); visible(progress_, true);
        lv_obj_set_pos(progress_track_, progress_x, progress_y);
        lv_obj_set_size(progress_track_, progress_width_, std::max(1, ui::px(3)));
        lv_obj_set_pos(progress_, progress_x, progress_y);
        lv_obj_set_size(progress_, std::max(1, int(progress_width_*std::clamp(now_.position/now_.duration,0.0f,1.0f))), std::max(1,ui::px(3)));
        ui::set_fill(progress_track_, tessera::Tone::NORMAL, theme::TRACK);
        ui::set_fill(progress_, tessera::Tone::NORMAL, theme::INK);
      }
      key(controls_x,controls_y,controls_w/3,row_,"",10,0xF04AE);
      key(controls_x+controls_w/3,controls_y,controls_w/3,row_,"",11,now_.state=="playing"?0xF03E4:0xF040A);
      key(controls_x+controls_w*2/3,controls_y,controls_w-controls_w*2/3,row_,"",12,0xF04AD);
    } else if (view_ == 1) {
      key(gap_,y,w_-gap_*2,row_,p_->text("search_music"),4);
      y += row_ + gap_*2;
      int available = std::max(1,h_-y-2*line_-row_-gap_*5);
      bool expanded = available >= 4*(line_*2+gap_);
      int recent_shown = std::min(recent_count_,expanded?2:1);
      int recommend_shown = std::min(recommend_count_,expanded?2:1);
      int slots = std::max(1,recent_shown)+std::max(1,recommend_shown);
      int item_h = std::max(1,std::min(available/slots,ui::mm(14)));
      word(2,p_->text("recent_songs"),gap_,y,w_-gap_*2);
      ui::set_font(words_[2],Font::TITLE);
      y += line_+gap_;
      if (!recent_shown) {
        word(3,p_->text("empty"),gap_*2,y,w_-gap_*4);
        ui::set_color(words_[3],theme::MUTED);
      } else for (int i=0;i<recent_shown;++i) menu_item(i,3+i*2,y+i*item_h,item_h);
      y += std::max(1,recent_shown)*item_h + gap_;
      word(7,p_->text("recommended_playlists"),gap_,y,w_-gap_*2);
      ui::set_font(words_[7],Font::TITLE);
      y += line_+gap_;
      if (!recommend_shown) {
        word(8,p_->text("empty"),gap_*2,y,w_-gap_*4);
        ui::set_color(words_[8],theme::MUTED);
      } else for (int i=0;i<recommend_shown;++i)
        menu_item(recent_count_+i,8+i*2,y+i*item_h,item_h);
      y += std::max(1,recommend_shown)*item_h+gap_;
      key(gap_,y,w_-gap_*2,row_,p_->text("library"),5);
    } else if (view_ == 2) {
      // Coordinate keyboard: uses only the SDK's filtered taps, no LVGL event handler.
      key(0,y,w_/2,row_,p_->text(kinds_[kind_]),21);
      word(1,query_.c_str(),w_/2,y+(row_-line_)/2,w_/2); y += row_;
      int kh = std::max(1,(h_-y-row_)/4);
      for (int i=0;i<36;++i) {
        char letter[2]={alphabet_[i],0}; int col=i%9;
        key(w_*col/9,y+(i/9)*kh,w_*(col+1)/9-w_*col/9,kh,letter,100+i);
      }
      key(0,h_-row_,w_/3,row_,p_->text("space"),22);
      key(w_/3,h_-row_,w_/3,row_,p_->text("delete"),23);
      key(w_*2/3,h_-row_,w_-w_*2/3,row_,p_->text("go"),24);
    } else {
      key(0,y,w_*2/3,row_,p_->text(view_==3?kinds_[kind_]:view_==4?"devices":categories_[category_]),20);
      key(w_*2/3,y,w_-w_*2/3,row_,p_->text(view_==3?"edit":"refresh"),view_==3?4:25);
      y += row_;
      int height = std::max(1,(h_-row_-y)/3);
      for (int i=0;i<count_;++i) {
        key(0,y+i*height,w_,height,"",30+i);
        auto *row_box = keys_[used_-1].box;
        lv_obj_set_parent(words_[1+i*2], row_box); lv_obj_set_parent(words_[2+i*2], row_box);
        int side = std::max(0,std::min(height-gap_*2,w_/6));
        bool art = pictures_[i] && !items_[i].image.empty();
        if (art) picture(i,items_[i].image,gap_,y+i*height+gap_,side);
        int left = art ? side+gap_*2 : gap_*2;
        word(1+i*2,items_[i].title.c_str(),left,gap_,w_-left-gap_);
        if(height >= line_*2+gap_*2) word(2+i*2,items_[i].artist.c_str(),left,gap_+line_,w_-left-gap_);
      }
      if (more_) key(w_/2,h_-row_,w_-w_/2,row_,p_->text("next"),27,0xF0142);
    }
  }
  void request(bool command, const char *operation="", const char *value="", const char *title="") {
    if (entity_.empty()) { message_=p_->text("choose"); paint(); return; }
    JsonDocument d;
    d["ask"] = command ? "call_service:spotify_mini.command" : "call_service:spotify_mini.browse";
    auto data = d["data"].to<JsonObject>(); data["entity_id"] = entity_.c_str();
    if (command) { data["operation"]=operation; data["value"]=value; data["title"]=title; }
    else {
      data["category"] = view_==3 ? "search" : view_==4 ? "devices" :
                         view_==5 ? categories_[category_] : "home";
      data["query"]=query_.c_str(); data["kind"]=kinds_[kind_]; data["offset"]=offset_;
      count_=0; more_=false;
    }
    command_=command; asked_=tessera::send(p_,d.as<JsonObjectConst>()); asked_at_=esphome::millis();
    message_=asked_?"":p_->text("failed"); paint();
  }
  void act(int action) {
    if (action==1) { asked_=0; view_=4; offset_=0; request(false); return; }
    if (action==2) { asked_=0; view_=1; offset_=0; request(false); return; }
    if (action==3) { on_back(); return; }
    if (action==4) { asked_=0; view_=2; message_.clear(); paint(); return; }
    if (action==5) { asked_=0; view_=5; category_=0; offset_=0; request(false); return; }
    if (asked_) return;
    if (action>=10 && action<=12) { static const char *ops[]={"previous","toggle","next"}; request(true,ops[action-10]); return; }
    if (action>=100 && action<136) { if(query_.size()<48) query_+=alphabet_[action-100]; paint(); return; }
    if (action==21) { kind_=(kind_+1)%4; paint(); return; }
    if (action==22) { if(query_.size()<48) query_+=' '; paint(); return; }
    if (action==23) { if(!query_.empty()) query_.pop_back(); paint(); return; }
    if (action==24) { if(query_.empty()) return; view_=3; offset_=0; request(false); return; }
    if (action==20) {
      if(view_==3) kind_=(kind_+1)%4;
      else if(view_==5) category_=(category_+1)%4;
      else return;
      offset_=0; request(false); return;
    }
    if (action==25) { request(false); return; }
    if (action==27) { offset_+=3; request(false); return; }
    if (action>=30 && action<30+count_) {
      auto &i=items_[action-30]; request(true,i.kind=="device"?"device":"play_uri",i.uri.c_str(),i.title.c_str());
    }
  }
  SpotifyMini *p_;
  Text entity_, query_, message_;
  Now now_;
  Key keys_[48];
  Item items_[4];
  lv_obj_t *parent_{}, *words_[12]{}, *pictures_[4]{}, *menu_bars_[3]{}, *art_placeholder_{}, *art_label_{},
           *progress_track_{}, *progress_{};
  int w_{},h_{},line_{},gap_{},row_{},used_{},view_{},category_{},kind_{},offset_{},count_{},recent_count_{},recommend_count_{};
  int progress_width_{};
  uint32_t asked_{},asked_at_{};
  bool more_{},command_{};
  static constexpr const char *categories_[4]={"playlists","recent","albums","local"};
  static constexpr const char *kinds_[4]={"track","artist","album","playlist"};
  static constexpr const char *alphabet_="abcdefghijklmnopqrstuvwxyz0123456789";
};
void SpotifyMini::setup() {
  add_tile("player",[this](){return new PlayerTile(this);});
  add_card("player",[this](){return new PlayerCard(this);},true);
}
void SpotifyMini::on_message(JsonObjectConst message) { if(card) card->answer(message); }
}
