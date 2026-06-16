// ============================================================
// HotelHub — глобальный JavaScript проекта
// Подключается на всех страницах через base.html
// Путь: static/js/main.js
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    console.log('HotelHub загружен');

    // Пример: подсветка активного пункта меню в навигации
    const links = document.querySelectorAll('.navbar nav a');
    links.forEach(function (link) {
        if (link.href === window.location.href) {
            link.style.opacity = '1';
            link.style.textDecoration = 'underline';
        }
    });
});
