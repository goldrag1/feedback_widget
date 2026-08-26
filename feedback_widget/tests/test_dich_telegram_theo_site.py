"""Một bench nhiều site ⇒ nơi nhận Telegram phải hỏi SITE, không hỏi thư mục nhà.

Vì sao có tệp này: `notifier._load_config` đọc `~/.claude/channels/telegram/` — thứ
thuộc về TÀI KHOẢN chạy bench, không thuộc về site. Trên bench nextstar có 5 site dùng
chung một tài khoản, nên góp ý của site demo và của khách thật rơi vào CÙNG một hộp
thoại và không ai phân biệt được. Khoá `feedback_telegram_chat_id` trong site_config
tách chúng ra; phép kiểm này khoá cả HAI chiều — có khai thì phải thắng, không khai thì
phải rơi về cấu hình chung (site cũ không được đổi hành vi).
"""

import unittest
from unittest import mock

from feedback_widget import notifier


class TestDichTelegramTheoSite(unittest.TestCase):
	def test_site_config_thang_cau_hinh_chung(self):
		with mock.patch.object(notifier, "_tu_site_config", return_value=("TOK-SITE", "-100999")), \
		     mock.patch.object(notifier, "ENV_PATH") as env, \
		     mock.patch.object(notifier, "ACCESS_PATH") as acc:
			env.exists.return_value = False
			acc.exists.return_value = False
			self.assertEqual(notifier._load_config(), ("TOK-SITE", "-100999"))

	def test_thieu_khoa_site_thi_roi_ve_cau_hinh_chung(self):
		with mock.patch.object(notifier, "_tu_site_config", return_value=(None, None)), \
		     mock.patch.object(notifier, "ENV_PATH") as env, \
		     mock.patch.object(notifier, "ACCESS_PATH") as acc:
			env.exists.return_value = True
			env.read_text.return_value = 'TELEGRAM_BOT_TOKEN="TOK-CHUNG"\n'
			acc.exists.return_value = True
			acc.read_text.return_value = '{"allowFrom": ["1665999873"]}'
			self.assertEqual(notifier._load_config(), ("TOK-CHUNG", "1665999873"))

	def test_chi_khai_chat_thi_van_dung_bot_chung(self):
		"""Trường hợp thật của site demo: cùng bot, khác nhóm nhận."""
		with mock.patch.object(notifier, "_tu_site_config", return_value=(None, "-100999")), \
		     mock.patch.object(notifier, "ENV_PATH") as env, \
		     mock.patch.object(notifier, "ACCESS_PATH") as acc:
			env.exists.return_value = True
			env.read_text.return_value = 'TELEGRAM_BOT_TOKEN="TOK-CHUNG"\n'
			acc.exists.return_value = True
			acc.read_text.return_value = '{"allowFrom": ["1665999873"]}'
			self.assertEqual(notifier._load_config(), ("TOK-CHUNG", "-100999"))

	def test_chat_id_dang_so_duoc_ep_ve_chuoi(self):
		"""Telegram đòi chat_id dạng chuỗi; site_config.json cho phép gõ số."""
		with mock.patch("frappe.get_conf", return_value={"feedback_telegram_chat_id": -1002233}):
			self.assertEqual(notifier._tu_site_config(), (None, "-1002233"))

	def test_khong_co_ngu_canh_site_thi_im_lang(self):
		"""Chạy ngoài ngữ cảnh site (worker chưa init) không được ném — góp ý vẫn phải lưu."""
		with mock.patch("frappe.get_conf", side_effect=RuntimeError("chưa init site")):
			self.assertEqual(notifier._tu_site_config(), (None, None))
