export default function PrivacyPage() {
  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 max-w-[720px] mx-auto w-full">
      <h1 className="text-2xl font-bold text-ink-100 mb-6">Политика конфиденциальности</h1>

      <div className="bg-surface rounded-card shadow-sm p-6 md:p-8 space-y-6 text-sm text-ink-60 leading-relaxed">
        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">1. Общие положения</h2>
          <p>Настоящая Политика конфиденциальности описывает, как FoodBox («Мы», «нас», «наш») собирает, использует и защищает вашу персональную информацию при использовании нашего сервиса.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">2. Собираемые данные</h2>
          <p className="mb-2">Мы можем собирать следующие данные:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Имя и контактная информация (email, номер телефона)</li>
            <li>Данные о местоположении (для поиска ближайших постаматов)</li>
            <li>История заказов и платёжные данные (через защищённый платёжный шлюз)</li>
            <li>Данные об использовании приложения</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">3. Использование данных</h2>
          <p className="mb-2">Собранные данные используются для:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Обработки и доставки ваших заказов</li>
            <li>Улучшения качества сервиса</li>
            <li>Отправки уведомлений о статусе заказа</li>
            <li>Персонализации предложений</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">4. Защита данных</h2>
          <p>Мы применяем технические и организационные меры для защиты ваших персональных данных от несанкционированного доступа, изменения или уничтожения. Данные банковских карт не хранятся на наших серверах.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">5. Передача данных третьим лицам</h2>
          <p>Мы не продаём и не передаём ваши персональные данные третьим лицам без вашего согласия, за исключением случаев, предусмотренных законодательством.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">6. Ваши права</h2>
          <p>Вы имеете право на доступ, исправление или удаление ваших персональных данных. Для этого обратитесь в нашу службу поддержки.</p>
        </section>

        <section>
          <h2 className="text-base font-bold text-ink-100 mb-2">7. Контакты</h2>
          <p>По вопросам конфиденциальности обращайтесь: <span className="text-primary font-semibold">privacy@foodbox.ru</span></p>
        </section>

        <p className="text-xs text-ink-40 pt-2 border-t border-line">Последнее обновление: май 2026</p>
      </div>
    </div>
  )
}
