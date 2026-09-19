document.addEventListener('DOMContentLoaded', () => {

    /* =========================================================
       PAGE LOADER
       ========================================================= */

    const loader = document.getElementById('pageLoader');

    if (loader) {
        setTimeout(() => {
            loader.classList.add('loader-hide');
        }, 250);
    }


    /* =========================================================
       BACK TO TOP
       ========================================================= */

    const top = document.getElementById('backToTop');

    window.addEventListener('scroll', () => {
        if (top) {
            top.style.display = window.scrollY > 500 ? 'grid' : 'none';
        }
    });

    if (top) {
        top.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }


    /* =========================================================
       SCROLL REVEAL
       ========================================================= */

    const observer = new IntersectionObserver(
        entries => entries.forEach(e => {

            if (e.isIntersecting) {
                e.target.classList.add('visible');
                observer.unobserve(e.target);
            }

        }),
        {
            threshold: .12
        }
    );

    document
        .querySelectorAll('.reveal')
        .forEach(el => observer.observe(el));


    /* =========================================================
       QUANTITY — INCREASE
       ========================================================= */

    document
        .querySelectorAll('[data-qty-plus]')
        .forEach(b => b.addEventListener('click', () => {

            const i = b.parentElement.querySelector('input');
            const max = parseInt(i.max) || 999999;

            i.value = Math.min(
                max,
                (parseInt(i.value) || 1) + 1
            );

        }));


    /* =========================================================
       QUANTITY — DECREASE
       ========================================================= */

    document
        .querySelectorAll('[data-qty-minus]')
        .forEach(b => b.addEventListener('click', () => {

            const i = b.parentElement.querySelector('input');

            i.value = Math.max(
                1,
                (parseInt(i.value) || 1) - 1
            );

        }));


    /* =========================================================
       ADD TO CART — SUBMIT BUTTON
       ========================================================= */

    document
        .querySelectorAll('form')
        .forEach(form => form.addEventListener('submit', () => {

            const btn = form.querySelector('.add-cart');

            if (btn) {
                btn.disabled = true;
                btn.dataset.original = btn.innerHTML;

                btn.innerHTML =
                    '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';
            }

        }));


    /* =========================================================
       PRODUCT SORTING
       ========================================================= */

    const sort = document.getElementById('productSort');
    const grid = document.getElementById('productGrid');

    if (sort && grid) {

        sort.addEventListener('change', () => {

            const items = [
                ...grid.querySelectorAll('.product-grid-item')
            ];

            const mode = sort.value;

            items.sort((a, b) =>
                mode === 'price-low'
                    ? parseFloat(a.dataset.price) -
                      parseFloat(b.dataset.price)

                    : mode === 'price-high'
                    ? parseFloat(b.dataset.price) -
                      parseFloat(a.dataset.price)

                    : mode === 'name'
                    ? a.dataset.name.localeCompare(b.dataset.name)

                    : 0
            );

            items.forEach(x => grid.appendChild(x));
        });
    }


    /* =========================================================
       DELETE CART ITEM CONFIRMATION
       ========================================================= */

    document
        .querySelectorAll('.delete-item')
        .forEach(b => b.addEventListener('click', e => {

            if (!confirm('Remove this product from your cart?')) {
                e.preventDefault();
            }

        }));

});
