/* ===========================================
   THE GOODY CO.
   Premium Chocolate Store
   main.js
=========================================== */

document.addEventListener("DOMContentLoaded", function () {

    console.log("THE GOODY CO. Loaded Successfully!");

    /* =====================================
       Navbar Shadow on Scroll
    ===================================== */

    const navbar = document.querySelector(".navbar");

    window.addEventListener("scroll", function () {

        if (window.scrollY > 40) {
            navbar.classList.add("shadow");
        } else {
            navbar.classList.remove("shadow");
        }

    });

    /* =====================================
       Back To Top Button
    ===================================== */

    const backToTop = document.getElementById("backToTop");

    if (backToTop) {

        window.addEventListener("scroll", function () {

            if (window.pageYOffset > 300) {
                backToTop.style.display = "block";
            } else {
                backToTop.style.display = "none";
            }

        });

        backToTop.addEventListener("click", function () {

            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });

        });

    }

    /* =====================================
       Product Search
    ===================================== */

    const search = document.getElementById("searchProduct");

    if (search) {

        search.addEventListener("keyup", function () {

            let filter = this.value.toLowerCase();

            let cards = document.querySelectorAll(".product-card");

            cards.forEach(function (card) {

                let title = card.querySelector(".product-title");

                if (!title) return;

                if (title.innerText.toLowerCase().includes(filter)) {

                    card.style.display = "block";

                } else {

                    card.style.display = "none";

                }

            });

        });

    }

    /* =====================================
       Quantity Buttons
    ===================================== */

    const plus = document.getElementById("plus");
    const minus = document.getElementById("minus");
    const qty = document.getElementById("quantity");

    if (plus && minus && qty) {

        plus.addEventListener("click", function () {

            qty.value = Number(qty.value) + 1;

        });

        minus.addEventListener("click", function () {

            if (Number(qty.value) > 1) {

                qty.value = Number(qty.value) - 1;

            }

        });

    }

    /* =====================================
       Image Zoom
    ===================================== */

    const productImage = document.querySelector(".product-image img");

    if (productImage) {

        productImage.addEventListener("mousemove", function () {

            this.style.transform = "scale(1.1)";
            this.style.transition = ".3s";

        });

        productImage.addEventListener("mouseleave", function () {

            this.style.transform = "scale(1)";

        });

    }

    /* =====================================
       Contact Form
    ===================================== */

    const contactForm = document.getElementById("contactForm");

    if (contactForm) {

        contactForm.addEventListener("submit", function () {

            alert("Thank you! Your message has been sent.");

        });

    }

    /* =====================================
       Newsletter
    ===================================== */

    const newsletter = document.getElementById("newsletterForm");

    if (newsletter) {

        newsletter.addEventListener("submit", function (e) {

            e.preventDefault();

            alert("Thank you for subscribing!");

            newsletter.reset();

        });

    }

    /* =====================================
       Confirm Delete
    ===================================== */

    const deleteButtons = document.querySelectorAll(".delete-item");

    deleteButtons.forEach(function (button) {

        button.addEventListener("click", function (e) {

            if (!confirm("Remove this product from cart?")) {

                e.preventDefault();

            }

        });

    });

    /* =====================================
       Product Card Animation
    ===================================== */

    const cards = document.querySelectorAll(".product-card");

    cards.forEach(function (card) {

        card.addEventListener("mouseenter", function () {

            card.style.transform = "translateY(-10px)";
            card.style.transition = ".3s";

        });

        card.addEventListener("mouseleave", function () {

            card.style.transform = "translateY(0px)";

        });

    });

    /* =====================================
       Add To Cart Animation
    ===================================== */

    const cartButtons = document.querySelectorAll(".add-cart");

    cartButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            button.innerHTML = "✔ Added";

            button.classList.remove("btn-warning");
            button.classList.add("btn-success");

            setTimeout(function () {

                button.innerHTML = "Add To Cart";

                button.classList.remove("btn-success");
                button.classList.add("btn-warning");

            }, 1500);

        });

    });

    /* =====================================
       Payment Method Toggle (Checkout)
    ===================================== */

    const paymentOptions = document.querySelectorAll(".payment-option");

    if (paymentOptions.length) {

        const hideAllPaymentBoxes = function () {
            document.querySelectorAll(".payment-details-box").forEach(function (box) {
                box.classList.add("d-none");
            });
        };

        hideAllPaymentBoxes();

        paymentOptions.forEach(function (option) {

            option.addEventListener("change", function () {

                hideAllPaymentBoxes();

                const targetSelector = option.getAttribute("data-target");

                if (targetSelector) {
                    const target = document.querySelector(targetSelector);
                    if (target) {
                        target.classList.remove("d-none");
                    }
                }

            });

        });

    }

    /* =====================================
       Scroll Reveal Animations
    ===================================== */

    const revealEls = document.querySelectorAll(
        ".category-card, .product-card, .feature-box, .testimonial-box, .offer-section .col-lg-6"
    );

    if (revealEls.length && "IntersectionObserver" in window) {

        revealEls.forEach(function (el) {
            el.classList.add("reveal");
        });

        const revealObserver = new IntersectionObserver(function (entries, observer) {

            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("reveal-visible");
                    observer.unobserve(entry.target);
                }
            });

        }, { threshold: 0.15 });

        revealEls.forEach(function (el) {
            revealObserver.observe(el);
        });

    }

    /* =====================================
       Checkout Validation
    ===================================== */

    const checkoutForm = document.getElementById("checkout-form");

    if (checkoutForm) {

        checkoutForm.addEventListener("submit", function (e) {

            const inputs = checkoutForm.querySelectorAll("input[required]");

            let valid = true;

            inputs.forEach(function (input) {

                if (input.value.trim() === "") {

                    valid = false;

                    input.style.border = "2px solid red";

                } else {

                    input.style.border = "";

                }

            });

            if (!valid) {

                e.preventDefault();

                alert("Please fill all required fields.");

            }

        });

    }

    /* =====================================
       Auto Hide Alerts
    ===================================== */

    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(function (alertBox) {

        setTimeout(function () {

            alertBox.style.display = "none";

        }, 4000);

    });

});