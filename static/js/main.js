// ============================================================
// HotelHub — глобальный JavaScript проекта
// Подключается на всех страницах через templates/base.html
// Путь: static/js/main.js
//
// Подсветка активного пункта меню теперь делается на сервере
// (см. templates/includes/navbar.html, request.resolver_match),
// поэтому здесь остаются только общие UX-улучшения для всех
// страниц hotels и rooms.
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    console.log('HotelHub загружен');

    // Автофокус на поле поиска, если оно пустое
    const searchInput = document.querySelector('.search-input');
    if (searchInput && !searchInput.value) {
        searchInput.focus();
    }

    // Мягкое появление карточек при загрузке страницы
    const cards = document.querySelectorAll('.card');
    cards.forEach(function (card, index) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(8px)';
        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        setTimeout(function () {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 40 * index);
    });
});
