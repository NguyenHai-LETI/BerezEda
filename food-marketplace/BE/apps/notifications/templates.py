from apps.notifications.constants import NotificationType

NOTIFICATION_TEMPLATES = {
    # Buyer notification templates (based on documentation)
    NotificationType.COMBO_PICKUP_DEADLINE_PASSED: {
        "title": "商品の受け取り期限が過ぎました",
        "content": (
            "受け取り予約されたロッカー名{locker_name}、商品No.{product_code} 商品名{product_name}の受け取り期限が過ぎました。恐縮ですが、お客様の注文ステータスを「受取完了」に変更させていただきます。\n\n"
        ),
        "shop_id": "{shop_id}",
    },
    NotificationType.PRODUCT_EXPIRED: {
        "title": "受け取り商品の消費期限が過ぎました ",
        "content": (
            "商品No.{product_code} 商品名{product_name}の消費期限が超過しました。安全のため、消費期限切れの商品の飲食は行わず、廃棄してください。"
        ),
    },
    NotificationType.NEW_COMBO_FROM_FAVORITE_STORE: {
        "title": "お気に入り店舗　新商品提供のお知らせ！ ",
        "content": (
            "お気に入り店舗{store_name}で新商品がアップされました。アプリからチェックしてみましょう！ "
        ),
    },
    NotificationType.COMBO_PICKUP_DEADLINE_APPROACHING: {
        "title": "商品の受け取り期限が残り5分です",
        "content": (
            "商品No.{product_code} 商品名{product_name}の受け取り期限が残り5分です。期限が過ぎると取り出し不可となりますので、お早めにロッカーへお越しください。\n"
            "商品を受け取りましたか？\n"
        ),
        "shop_id": "{shop_id}",
        "order_id": "{order_id}",
        "pickup_code": "{order_pickup_code}",
    },
    NotificationType.ORDER_CANCELED: {
        "title": "注文がキャンセルされました ",
        "content": (
            "商品No.{product_code}商品名{product_name}のキャンセルが成立し、返金手続きを開始しました。返金完了までには数日かかる場合があります。"
        ),
    },
    # Store notification templates (based on documentation)
    NotificationType.USER_BUY_COMBO: {
        "title": "商品No.{product_code} 商品名 {product_name} が予約されました",
        "content": (
            "商品No.{product_code} 商品名 {product_name} が予約されました。受け取り成功までお待ちください。"
        ),
    },
    NotificationType.USER_CANCELLED_COMBO: {
        "title": "商品No.{product_code} 商品名 {product_name} がキャンセルされました ",
        "content": (
            "予約商品の商品No.{product_code} 商品名 {product_name} がキャンセルされました。 "
        ),
    },
    NotificationType.COMBO_PICKUP_COMPLETED: {
        "title": "商品No.{product_code} 商品名 {product_name} が受け取り完了しました ",
        "content": (
            "商品No.{product_code} 商品名 {product_name} の受け取りが成功しました！"
        ),
    },
    NotificationType.COMBO_EXPIRED_SALES: {
        "title": "商品No.{product_code} 商品名 {product_name} は予約されませんでした ",
        "content": (
            "商品No.{product_code} 商品名 {product_name} は販売時間を迎えましたが、予約成立いたしませんでした。"
        ),
    },
    NotificationType.NEW_REVIEW_RECEIVED: {
        "title": "Новый отзыв на набор «{product_name}»",
        "content": 'Покупатель оставил отзыв на набор «{product_name}»: "{review_content}"',
    },
    NotificationType.COMBO_PLACEMENT_DEADLINE_APPROACHING: {
        "title": "残り５分でロッカー入庫期限を迎えます ",
        "content": (
            "ロッカー名 {locker_name} 部屋番号 {unit_number} への入庫期限が残り５分を迎えました。お早めにロッカーへお越しいただき商品入庫をお願いいたします。"
        ),
    },
    NotificationType.PRODUCT_EXPIRY_REACHED: {
        "title": "商品の期限到達のお知らせ（{product_master_name}）",
        "content": (
            "ご購入いただいた {product_master_name} は、期限を迎えました。安全のため、期限内にお召し上がりいただけましたでしょうか？現在の状況を以下よりお知らせください。"
        ),
    },
}
