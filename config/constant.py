HEADLESS = True

API_URL = "https://staging.sosyokmy.com/whitelabel-staging-2/public"

CREDENTIALS = {
    "valid_user": {
        "username": "EmoKing1",
        "password": "EmoKing1",
        "fullname": "EmoKing1",
    },
    "invalid_user": {
        "username": "Try12345",
        "password": "Adelalala00",
    },
    "luffy_user": {
        "username": "LuffyTest2",
        "password": "LuffyTest2",
    },
    "account_number": {
        "valid_account_number": "165364789753",
        "invalid_account_number": "abc",
        "duplicated_account_number": "165364789753",
    },
    "duplicated_user": {
        "username": "Settlee1",
        "password": "Settlee1",
        "confirm_password": "Settlee1",
        "fullname": "Incomplete3",
        "phone_number": "166189753",
    },
    "complete_turnover": {
        "username": "Settlee1",
        "password": "Settlee1",
    },
    "incomplete_turnover": {  #can remove
        "username": "Incomplete3",
        "password": "Incomplete3",
    },
    "invalidDigit_password": {
        "password": "Jo123"
    },
    "Password_WithoutCapital": {
        "password": "bello321"
    },
    "Password_WithoutNumber": {
        "password": "ABCdefggf"
    },
    "revert_batch_size": {
        "batch_size": "10"
    },
    "transfer_amount": {
        "amount": "2.0"
    },
    "deposit": {
        "invalid_voucher": "abc",
    },
    "image_url": "https://picsum.photos/200/300",
    "image_path": "test_deposit.jpg",
    "BO_testing_url": "https://staging.sosyokmy.com/whitelabel-test/public",
    "BO_base_url": "https://staging.sosyokmy.com/whitelabel-staging-2/public",
    "RejectDepositRequest": "{BO_base_url}/api/recharge/refuse/batch?user_ids[]={ID}&pass=123456",
    "ProcessingDepositRequest": "{BO_base_url}/api/recharge/process/batch?user_ids[]={ID}&pass=123456",
    "ApproveDepositRequest": "{BO_base_url}/api/recharge/approve?user_ids[]={ID}&pass=123456",
    "RejectWithdrawRequest": "{BO_base_url}/api/withdraw/refuse/batch?user_ids[]={ID}&pass=123456",
    "ProcessingWithdrawRequest": "{BO_base_url}/api/withdraw/process/batch?user_ids[]={ID}&pass=123456",
    "ApproveWithdrawRequest": "{BO_base_url}/api/withdraw/approve?user_ids[]={ID}&pass=123456",
    "CheckTurnover": "{BO_base_url}/api/check-turnover?pass=123456&user_id={ID}&lang={language}",
    "ModifyTurnover": "{BO_base_url}/api/modify-turnover?pass=123456&user_id={userID}&turnover_id={turnover_id}&action={action}",
    "SpecifyDateHistory": "{BO_base_url}/api/filter-records-by-date?type={record_type_value}&page=1&from={start_date}&to={end_date}",
    "DateHistory": "{BO_base_url}/api/filter-records-by-date?type={record_type_value}&page=1&date={date_option_id}",
    "PlaceBet": "{BO_base_url}/api/simulate-game-records?passcode=99999&user_id={userID}&amount={transfer_amount}&type={type}&provider_id={game_id}&game_record_date={game_record_date}",
    "CreateDownline": "{BO_base_url}/api/qa-generate-user?pass=123456&user_id={userID}&t2=1&t3=1",
    "CreateRebate": "{BO_base_url}/api/qa-calculate-rebate?pass=123456&user_ids={userID}&month={current_month}",
    "CheckRebatePercentage": "{BO_base_url}/api/qa-rebate-list?pass=123456",
    "Get4dHistory": "{BO_base_url}/api/user-4d-records-history",
    "Add4dCards": "{BO_base_url}/api/qa-redeem-fourd-card",
    "Bet4d": "{BO_base_url}/api/qa-bet-fourd",
    "UpdateBetResult": "{BO_base_url}/api/qa-update-bet-result",
    "GetAllPromotion": "{BO_base_url}/api/promotion",
    "GetUser": "{BO_base_url}/api/user",
}

LANGUAGE_SETTINGS = {
    "cn": {
        "home_url": "https://whitelabel-ui.vercel.app/cn/home",
        "login_url": "https://whitelabel-ui.vercel.app/cn/login",
        "fields": {
            "login_id": "用户名",
            "password": "密码",
            "confirm_password": "确认密码",
            "full_name": "全名",
            "phone_no": "手机号",
        },
        "update_data": {
            "新用户名": "Employee",
            "新手机号码": "1234354232",
            "新电子邮件": "employee00@gmail.com",
        },
        "password_data": {
            "当前密码": "Try123456789",  # ask to change language
            "新密码": "Halo2222",
            "确认新密码": "Halo2222",
        },
        "errors": {
            "duplicate_account": "用户名 已经存在。",
            "password_less_than_8": "密码 至少为 8 个字符。",
            "password_format_wrong": "密码 格式不正确。",
            "invalid_phone_format": "电话 格式不正确。",
            "phone_already_exists": "电话 已经存在。",
            "invalid_username": "用户名 格式不正确。",
            "username_larger_than_12": "用户名 不能大于 12 个字符。",
            "registration_success": "注册成功",
            "invalid_login": "密码或名称错误",
            "field_missing": "Please fill in this field.",
            "unmatch_password": "您输入的密码和确认密码不匹配!",
            "new_password_invalid_length": "新密码必须包含最少8个字符!",
            "invalid_new_password": "新密码必须包含至少1个大写字母、1个小写字母和1个数字!",
            "deposit_less_than_30": "最低充值额：RM30",
            "deposit_more_than_50000": "最大充值额：RM50000",
            "empty_fields": "请输入所有必填字段 (*)",
            "duplicated_account": "此卡已存在",
            "max_accounts": "最多只能绑定5张银行卡",
            "insufficient_reload": "最低转账金额应为",
            "large_file_type": "文件大小必须小于 5MB",
            "cancelPaymentGateway": "付款状态： 失败",
            "withdraw_less_than_50": "最低提款：RM50",
            "is_required": "不能为空",
            "register_error": "注册失败",
            "withdraw_turnover_incomplete": "您未达到打码量，无法提现",
            "insufficient_main_wallet": "主钱包余额不足, 若其他钱包有余额, 将其转入主钱包！",
            "from_wallet_empty": "自是必填的",
            "to_wallet_empty": "转移至是必填的",
            "amount_empty": "金额是必填的",
            "transfer_exceed_balance_limit": "您的余额不足。",
            "amount_decimal_places": "金额必须是数字 | 金额只接受2位小数",
            "zero_amount_invalid": "输入的金额无效。",
            "transfer_same_wallet": "不能从同一游戏钱包转移。",
            "bonus_locked": "奖金已锁定",
            "system_error": "系统异常，请联系客服。",
            "setting_password_empty": "不能为空",
            "revert_error": "发生错误，请联系客服"
        },
        "success": {
            "withdraw_success": "提交成功",
            "register_success": "注册成功",
            "reset_password": "更换成功!"
        },
        "messages": {
            "forgot_password": "我忘记了密码"
        },
        "change_profile": {
            "gallery": "从相册选择",
            "photo": "拍照"
        },
        "check_in": {
            "checked_in_days": "你已连续签到",
            "checked_in": "已签到",
            "check_in_now": "马上签到",
            ":": "："
        },
        "deposit": {
            "select_payment_gateway": "选择支付通道"
        },
        "password_fields": {
            "current_password": "当前密码",
            "new_password": "新密码",
            "confirm_new_password": "确认新密码"
        },
        "gift_redemption": {
            "sort_by": "排序方式",
            "sort_by_my_favorite": "我的收藏",
            "sort_by_lowest_points": "最低币",
            "sort_by_highest_points": "最高币",
            "sort_by_last_updated": "最新",
            "4d": "万字卡",
            "voucher": "购物券",
            "redeem": "领取",
            "search": "搜索",
            "contact_customer_service": "联络客服",
            "successful": "成功",
            "redirect_to_whatsapp": "转到WhatsApp",
            "close": "关闭",
            "insufficient_points": "礼品币 不足",
        },
        "daily_mission": {
            "success": "奖励领取成功。",
            "claimed": "已领取",
            "claim_more": "如何获得更多",
            "upgrade": "升级并获得更多",
            "go": "前往",
            "claim": "获取",
            "view_missions": "查看完整任务"
        },
        "vip_member_level": {
            "surpassed_subtitle": "您已经超越该等级",
            "normal_subtitle": "注册后将自动成为普通会员",
            "topup_subtitle": "还差充值RM{topup_more}升级为{next_vip_name}会员",
            "qualification_text": "所有新会员充值至少{recharge_amount}皆可升级成为永久{vip_name}会员",
            "requirement_text": "至少存入{recharge_amount}的最低金额",
            "upgrade_button": "充值升级",
            "reached_button": "已达成"
        },
        "history": {
            "no_record": "No data available",
        },
        "4d":{
            "card_name": "BOBO万字卡",
            "4d_card": "万字卡",
            "4d_card_receipt": "万字卡",
            "win_title": "恭喜你中万字啦!",
            "win_desc": "下注号码: {bet_number}",
        },
        "promotion": {
            "claim": "领取",
        },
        "profile": {
            "balance": "总余额",
            "balance_value": "MYR {amount}",
            "bbpoints": "BB点数",
            "deposit": "存款",
            "withdraw": "提款",
            "transfer": "转移",
            "rebate": "即时反水",
            "promotion": "啵啵优惠",
            "lotto_record": "万字卡记录",
            "gift_redemption": "礼品兑换",
            "live_agent": "客服",
        },
    },
    "en": {
        "home_url": "https://whitelabel-ui.vercel.app/en/home",
        "login_url": "https://whitelabel-ui.vercel.app/en/login",
        "fields": {
            "login_id": "Username",
            "password": "Password",
            "confirm_password": "Confirm Password",
            "full_name": "Full Name",
            "phone_no": "Telephone Number",
        },
        "update_data": {
            "New Username": "Employee",
            "New Mobile No": "1234354232",
        },
        "password_data": {
            "Current Password": "Try123456789",  # ask to change language
            "New Password": "Halo2222",
            "Confirm New Password": "Halo2222",
        },
        "errors": {
            "duplicate_account": "The username has already been taken.",  # ask to change
            "password_less_than_8": "The password must be at least 8 characters.",
            "password_format_wrong": "The password format is invalid.",
            "invalid_phone_format": "The phone format is invalid.",
            "phone_already_exists": "The phone has already been taken.",
            "invalid_username": "The username format is invalid.",
            "username_larger_than_12": "The username may not be greater than 12 characters.",
            "registration_success": "Register Successful",
            "invalid_login": "Name or Password incorrect",
            "field_missing": "Please fill in this field.",
            "unmatch_password": "Password not match!",
            "invalid_new_password": "New Password must contain at least 1 uppercase letter, 1 lowercase letter and 1 number!",
            "new_password_invalid_length": "New password must contain at least 8 characters!",
            "deposit_less_than_30": "Minimum Deposit: RM30",
            "deposit_more_than_50000": "Maximum Deposit: RM50000",
            "empty_fields": "Please enter all required fields (*)",
            "duplicated_account": "Card Existed",
            "max_accounts": "You can bind up to 5 bank cards",
            "insufficient_reload": "The min transfer amount should be",
            "large_file_type": "File size must be less than 5MB",
            "cancelPaymentGateway": "Payment Status: Failed",
            "withdraw_less_than_50": "Minimum Withdraw: RM50",
            "is_required": "is required",
            "register_error": "Register Failed",
            "withdraw_turnover_incomplete": "You haven't hit the turnover target, unable to withdraw",
            "insufficient_main_wallet": "Main wallet balance is insufficient, if other wallets have balance, transfer them to the main wallet!",
            "from_wallet_empty": "Transfer from is required",
            "to_wallet_empty": "Transfer to is required",
            "amount_empty": "Amount is required",
            "transfer_exceed_balance_limit": "You have insufficient balance.",
            "transfer_invalid_amount": "Amount must be a number | Amount only accept for 2 decimal places",
            "zero_amount_invalid": "The amount entered is invalid.",
            "transfer_same_wallet": "You cannot transfer between the same wallet.",
            "bonus_locked": "Bonus locked",
            "system_error": "System error, please contact customer service.",
            "setting_password_empty": "is required",
            "revert_error": "An error occurred, please contact customer service"
        },
        "success": {
            "withdraw_success": "Withdrawal Submitted",
            "register_success": "Register Successful",
            "reset_password": "Change Successful!"
        },
        "messages": {
            "forgot_password": "I have forgotten my password"
        },
        "change_profile": {
            "gallery": "Pick From Photos",
            "photo": "Take Photo"
        },
        "check_in": {
            "checked_in_days": "Checked in",
            "checked_in": "Checked In",
            "check_in_now": "Check in now",
            ":": ": "
        },
        "deposit": {
            "select_payment_gateway": "Select payment gateway"
        },
        "password_fields": {
            "current_password": "Current Password",
            "new_password": "New Password",
            "confirm_new_password": "Confirm New Password"
        },
        "gift_redemption": {
            "sort_by": "Sort By",
            "sort_by_my_favorite": "My Favourite",
            "sort_by_lowest_points": "Lowest Points",
            "sort_by_highest_points": "Highest Points",
            "sort_by_last_updated": "Last Updated",
            "4d": "4D",
            "voucher": "Voucher",
            "redeem": "Redeem",
            "search": "Search",
            "contact_customer_service": "contact customer service",
            "successful": "Successful",
            "redirect_to_whatsapp": "Redirect to WhatsApp",
            "close": "Close",
            "insufficient_points": "Gift Coins are not enough",
        },
        "daily_mission": {
            "success": "Reward claimed successfully.",
            "claimed": "Claimed",
            "claim_more": "How to Claim More?",
            "upgrade": "Upgrade & Get",
            "go": "Go",
            "claim": "Claim Now",
            "view_missions": "View Missions"
        },
        "vip_member_level": {
            "surpassed_subtitle": "You have surpassed this level",
            "normal_subtitle": "Become Normal member after register",
            "topup_subtitle": "Still need topup RM{topup_more} to upgrade to {next_vip_name} member",
            "qualification_text": "Minimum deposit at least RM{recharge_amount} become lifetime {vip_name} member",
            "requirement_text": "At least deposit minimum amount RM{recharge_amount}",
            "upgrade_button": "Topup & Upgrade",
            "reached_button": "Reached"
        },
        "history": {
            "no_record": "No data available",
        },
        "4d":{
            "card_name": "BOBO Card",
            "4d_card": "4D Card",
            "4d_card_receipt": "4D Card",
            "win_title": "Congrats! You Won!",
            "win_desc": "Bet Number: {bet_number}",
        },
        "promotion": {
            "claim": "Claim",
        },
        "profile":{
            "balance": "Balance",
            "balance_value": "MYR {amount}",
            "bbpoints": "BB Points",
            "deposit": "Deposit",
            "withdraw": "Withdraw",
            "transfer": "Transfer",
            "rebate": "Rebate",
            "promotion": "Promotion",
            "lotto_record": "Lotto Record",
            "gift_redemption": "Gift Redemption",
            "live_agent": "Live Agent",
        },
    },
    "bm": {
        "home_url": "https://whitelabel-ui.vercel.app/bm/home",
        "login_url": "https://whitelabel-ui.vercel.app/bm/login",
        "fields": {
            "login_id": "Nama Pengguna",
            "password": "Kata Laluan",
            "confirm_password": "Sahkan Kata Laluan",
            "full_name": "Nama Penuh",
            "phone_no": "Nombor Telefon",
        },
        "update_data": {
            "Baru Name": "Employee",
            "Baru Mobile No": "1234354232",
            "Baru Emel": "employee00@gmail.com",
        },
        "password_data": {
            "Kata Laluan Semasa": "Try123456789",
            "Kata Laluan Baru": "Halo2222",
            "Sahkan Kata Laluan Baru": "Halo2222",
        },
        "errors": {
            "duplicate_account": "Isian username sudah ada sebelumnya.",
            "password_less_than_8": "Isian password harus minimal 8 karakter.",
            "password_format_wrong": "Format isian password tidak valid.",
            "invalid_phone_format": "Format isian phone tidak valid.",
            "phone_already_exists": "Isian phone sudah ada sebelumnya.",
            "invalid_username": "Format isian username tidak valid.",
            "username_larger_than_12": "Isian username seharusnya tidak lebih dari 12 karakter.",
            "registration_success": "Daftar berjaya",
            "invalid_login": "Nama pengguna atau kata laluan salah",
            "field_missing": "Please fill in this field.",
            "unmatch_password": "Kata Laluan tak sama!",
            "invalid_new_password": "Kata Laluan Baru mesti mengandungi sekurang-kurangnya 1 huruf besar, 1 huruf kecil dan 1 nombor!",
            "new_password_invalid_length": "Kata laluan baru mesti mengandungi paling kurang 8 aksara!",
            "deposit_less_than_30": "Tambah Nilai Minimum: RM30",
            "deposit_more_than_50000": "Tambah Nilai Maksimum: RM50000",
            "empty_fields": "Sila masukkan semua medan (*)",
            "duplicated_account": "Kad Telah Wujud",
            "max_accounts": "Anda boleh mendaftar sehingga 5 kad bank",
            "insufficient_reload": "Jumlah pemindahan minimum harus",
            "large_file_type": "Saiz fail mestilah kurang daripada 5MB",
            "cancelPaymentGateway": "Status Pembayaran: Gagal",
            "withdraw_less_than_50": "Minimum dikeluar: RM50",
            "is_required": "is required",
            "register_error": "Daftar gagal",
            "withdraw_turnover_incomplete": "Anda belum mencapai sasaran pusing ganti, tidak boleh mengeluarkan wang",
            "insufficient_main_wallet": "Baki dompet utama tidak mencukupi, jika dompet lain mempunyai baki, sila pindahkan ke dompet utama!",
            "from_wallet_empty": "Dari tidak boleh kosong",
            "to_wallet_empty": "Ke tidak boleh kosong",
            "amount_empty": "Jumlah tidak boleh kosong",
            "transfer_exceed_balance_limit": "Anda tidak mempunyai cukup baki.",
            "amount_decimal_places": "Jumlah harus berupa nombor | Jumlah hanya menerima 2 tempat perpuluhan",
            "zero_amount_invalid": "Amaun yang dimasukkan tidak sah.",
            "transfer_same_wallet": "Tidak boleh pindah antara dompet permainan yang sama.",
            "bonus_locked": "Bonus ditutup",
            "system_error": "Ralat sistem, sila hubungi perkhidmatan pelanggan.",
            "transfer_rollback": "Deposit ke {game_name} gagal, tetapi jumlahnya telah berjaya dikembalikan ke main.",
            "setting_password_empty": "Tidak boleh kosong",
            "revert_error": "Ralat berlaku, sila hubungi perkhidmatan pelanggan."
        },
        "success": {
            "withdraw_success": "Pengeluaran Dihantar",
            "register_success": "Daftar berjaya",
            "reset_password": "Tukan Berjaya!"
        },
        "messages": {
            "forgot_password": "Saya telah terlupa kata laluan saya"
        },
        "change_profile": {
            "gallery": "Pilih Dari Album",
            "photo": "Ambil Gambar"
        },
        "check_in": {
            "checked_in_days": "Sudah Check In",
            "checked_in": "Sudah Check In",
            "check_in_now": "Check In",
            ":": ": "
        },
        "deposit": {
            "select_payment_gateway": "Pilih Gateway Pembayaran"
        },
        "password_fields": {
            "current_password": "Kata Laluan Semasa",
            "new_password": "Kata Laluan Baru",
            "confirm_new_password": "Sahkan Kata Laluan Baru"
        },
        "gift_redemption": {
            "sort_by": "Susun",
            "sort_by_my_favorite": "Suka",
            "sort_by_lowest_points": "Point Terendah",
            "sort_by_highest_points": "Point Tertinggi",
            "sort_by_last_updated": "Paling Baru",
            "4d": "4D",
            "voucher": "Voucher",
            "redeem": "Tebus",
            "search": "Cari",
            "contact_customer_service": "hubungi customer service",
            "successful": "Berjaya",
            "redirect_to_whatsapp": "Pindah ke WhatsApp",
            "close": "Tutup",
            "insufficient_points": "Koin Hadiah tidak mencukupi",
        },
        "daily_mission": {
            "success": "Reward berjaya diklaim.",
            "claimed": "Dituntut",
            "claim_more": "Cara Menuntut Lebih Banyak?",
            "upgrade": "Upgrade & tuntut",
            "go": "Jom",
            "claim": "Klaim",
            "view_missions": "Lihat Semua Misi"
        },
        "vip_member_level": {
            "surpassed_subtitle": "Anda telah melepasi Level ini",
            "normal_subtitle": "Selepas daftar akan jadi member biasa",
            "topup_subtitle": "Topup lagi RM{topup_more} naik ke Ahli {next_vip_name}",
            "qualification_text": "Deposit RM{recharge_amount} jadi Ahli {vip_name} kekal",
            "requirement_text": "minima deposit RM{recharge_amount}",
            "upgrade_button": "Topup",
            "reached_button": "Level Terkini"
        },
        "history": {
            "no_record": "No data available",
        },
        "4d":{
            "card_name": "BOBO Kad",
            "4d_card": "4D Kad",
            "4d_card_receipt": "4D Card",
            "win_title": "Tahniah! Anda Menang!",
            "win_desc": "Bet Nombor: {bet_number}",
        },
        "promotion": {
            "claim": "Tuntut",
        },
        "profile":{
            "balance": "Jumlah Baki",
            "balance_value": "MYR {amount}",
            "bbpoints": "BB Point",
            "deposit": "Deposit",
            "withdraw": "Cuci",
            "transfer": "Pindahan",
            "rebate": "Rebat",
            "promotion": "Promosi",
            "lotto_record": "4D Transaksi",
            "gift_redemption": "Hadiah BoBo",
            "live_agent": "Live Agent",
        },
    },
}


PROFILE_URL = {
    "large_image_url": "https://sample-files.com/downloads/images/jpg/landscape_hires_4000x2667_6.83mb.jpg",
    "replace_image_url": "https://bobo-bucket.s3.ap-southeast-1.amazonaws.com/whitelabel/default-profile/AvatarP1.png",
    "valid_image_url": "https://bobo-bucket.s3.ap-southeast-1.amazonaws.com/chatbot/chatbot_avatar.png",
    "invalid_format_url": "https://sample-files.com/downloads/documents/txt/simple.txt",
}

LIVE_AGENT_URL = {
    "chatbot_base_url": "https://dev.whitelabel-dev.com/chatbot/",
    "whatsapp_base_url": "https://api.whatsapp.com/send/",
    "telegram_base_url": "https://t.me/",
    "profile_whatsapp_url": "https://api.whatsapp.com/send/?phone=60104254518&text&type=phone_number&app_absent=0",
}

FOUR_D_PRIZES = [3400,1200,600,210,80]