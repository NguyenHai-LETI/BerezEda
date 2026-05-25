export default function TermsPage() {
  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 max-w-[720px] mx-auto w-full">
      <h1 className="text-2xl font-bold text-ink-100 mb-6">Условия использования</h1>

      <div className="bg-surface rounded-card shadow-sm p-6 md:p-8 space-y-6 text-sm text-ink-60 leading-relaxed">
        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">1. Принятие условий</h2>
          <p>Используя сервис FoodBox, вы соглашаетесь с настоящими Условиями использования. Если вы не согласны с условиями, пожалуйста, не используйте наш сервис.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">2. Описание сервиса</h2>
          <p>FoodBox — платформа для продажи продовольственных наборов со скидкой от ресторанов и кафе. Мы связываем покупателей с продавцами через сеть постаматов для удобного самовывоза.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">3. Регистрация и аккаунт</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Вы обязаны предоставить достоверную информацию при регистрации</li>
            <li>Вы несёте ответственность за безопасность своего аккаунта</li>
            <li>Один пользователь может иметь только один аккаунт</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">4. Заказы и оплата</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>После оплаты заказ считается подтверждённым</li>
            <li>Вы обязаны забрать заказ в указанное время</li>
            <li>Невостребованные заказы могут быть отменены без возврата средств</li>
            <li>Возврат средств возможен только в случае ошибки на стороне продавца</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">5. Поведение пользователей</h2>
          <p>Пользователи обязуются не использовать сервис для:</p>
          <ul className="list-disc pl-5 space-y-1 mt-2">
            <li>Мошеннических действий</li>
            <li>Нарушения прав других пользователей</li>
            <li>Распространения вредоносного контента</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">6. Ограничение ответственности</h2>
          <p>FoodBox не несёт ответственности за качество товаров продавцов. Все претензии по качеству направляйте через форму обратной связи.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">7. Изменение условий</h2>
          <p>Мы оставляем за собой право изменять настоящие Условия. О существенных изменениях мы уведомим вас по электронной почте.</p>
        </section>

        <p className="text-xs text-ink-40 pt-2 border-t border-line">Последнее обновление: май 2026</p>
      </div>
    </div>
  )
}
