/**
 * Departmental SIWES Assistant (DSA)
 * Phase 3 — Client Interaction Layer
 * Powered by ShinkomaniaPlug
 */

document.addEventListener("DOMContentLoaded", () => {
    /* ======================================================================
       1. MOBILE NAVIGATION
       ====================================================================== */

    const mobileToggle = document.querySelector(".mobile-toggle");
    const navMenu = document.querySelector(".nav-menu");
    const primaryNavigation = document.getElementById("primary-navigation");

    const closeMobileMenu = () => {
        if (!mobileToggle || !navMenu) return;

        navMenu.classList.remove("active");
        mobileToggle.setAttribute("aria-expanded", "false");
        mobileToggle.setAttribute("aria-label", "Open navigation menu");

        document.body.classList.remove("mobile-nav-open");
    };

    const openMobileMenu = () => {
        if (!mobileToggle || !navMenu) return;

        navMenu.classList.add("active");
        mobileToggle.setAttribute("aria-expanded", "true");
        mobileToggle.setAttribute("aria-label", "Close navigation menu");

        document.body.classList.add("mobile-nav-open");
    };

    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener("click", () => {
            const isOpen =
                mobileToggle.getAttribute("aria-expanded") === "true";

            if (isOpen) {
                closeMobileMenu();
            } else {
                openMobileMenu();
            }
        });

        navMenu.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                closeMobileMenu();
            });
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeMobileMenu();

                if (
                    mobileToggle.getAttribute("aria-expanded") === "true"
                ) {
                    mobileToggle.focus();
                }
            }
        });

        document.addEventListener("click", (event) => {
            const isOpen =
                mobileToggle.getAttribute("aria-expanded") === "true";

            if (!isOpen) return;

            const clickedInsideNavigation =
                primaryNavigation &&
                primaryNavigation.contains(event.target);

            const clickedToggle =
                mobileToggle.contains(event.target);

            if (!clickedInsideNavigation && !clickedToggle) {
                closeMobileMenu();
            }
        });

        window.addEventListener("resize", () => {
            if (window.innerWidth > 1080) {
                closeMobileMenu();
            }
        });
    }


    /* ======================================================================
       2. NIGERIAN CITY SUGGESTIONS

       These are convenience suggestions only.

       They are intentionally NOT treated as an authoritative nationwide
       location dataset. A complete location architecture can be introduced
       later as DSA's placement intelligence expands.
       ====================================================================== */

    const stateCitiesMap = {
        "FCT Abuja": [
            "Abuja",
            "Garki",
            "Wuse",
            "Maitama",
            "Gudu",
            "Jabi",
            "Kubwa",
            "Gwagwalada"
        ],

        "Lagos": [
            "Lagos (Yaba)",
            "Lagos (Ikeja)",
            "Lagos (Lekki)",
            "Lagos (Victoria Island)",
            "Lagos Island",
            "Surulere",
            "Ikorodu"
        ],

        "Kaduna": [
            "Kaduna",
            "Zaria",
            "Kafanchan",
            "Sabon Gari"
        ],

        "Kano": [
            "Kano",
            "Bompai",
            "Nassarawa",
            "Fagge"
        ],

        "Oyo": [
            "Ibadan",
            "Ogbomoso",
            "Oyo",
            "Iseyin"
        ],

        "Rivers": [
            "Port Harcourt",
            "Obio-Akpor",
            "Eleme",
            "Bonny"
        ],

        "Enugu": [
            "Enugu",
            "Nsukka",
            "Udi"
        ],

        "Ogun": [
            "Abeokuta",
            "Ota",
            "Sagamu",
            "Ijebu Ode"
        ],

        "Edo": [
            "Benin City",
            "Ekpoma",
            "Auchi"
        ],

        "Delta": [
            "Warri",
            "Asaba",
            "Ughelli",
            "Sapele"
        ],

        "Anambra": [
            "Awka",
            "Onitsha",
            "Nnewi"
        ],

        "Plateau": [
            "Jos",
            "Bukuru"
        ],

        "Kwara": [
            "Ilorin",
            "Offa"
        ],

        "Akwa Ibom": [
            "Uyo",
            "Eket",
            "Ikot Ekpene"
        ],

        "Cross River": [
            "Calabar",
            "Ikom"
        ]
    };

    const stateSelect =
        document.getElementById("stateSelect") ||
        document.querySelector('select[name="state"]') ||
        document.querySelector('select[name="preferred_state"]');

    const cityInput =
        document.getElementById("cityInput") ||
        document.querySelector('input[name="city"]') ||
        document.querySelector('input[name="preferred_city"]');

    const cityDatalist =
        document.getElementById("cityList");

    const refreshCitySuggestions = () => {
        if (!stateSelect || !cityDatalist) return;

        const selectedState = stateSelect.value;

        cityDatalist.innerHTML = "";

        const suggestedCities =
            stateCitiesMap[selectedState] || [];

        suggestedCities.forEach((city) => {
            const option = document.createElement("option");
            option.value = city;

            cityDatalist.appendChild(option);
        });
    };

    if (stateSelect && cityDatalist) {
        refreshCitySuggestions();

        stateSelect.addEventListener(
            "change",
            refreshCitySuggestions
        );
    }

    /*
     * Keep cityInput referenced intentionally.
     * Some templates may currently provide the input before the datalist
     * architecture is expanded later.
     */
    void cityInput;


    /* ======================================================================
       3. FLASH MESSAGES
       ====================================================================== */

    const alerts =
        document.querySelectorAll(".flash-container .alert");

    alerts.forEach((alert) => {
        const removeAlert = () => {
            if (!alert.isConnected) return;

            alert.style.opacity = "0";
            alert.style.transform = "translateY(-6px)";

            window.setTimeout(() => {
                if (alert.isConnected) {
                    alert.remove();
                }
            }, 250);
        };

        window.setTimeout(removeAlert, 6000);
    });


    /* ======================================================================
       4. MODALS
       ====================================================================== */

    let activeModal = null;
    let modalTriggerElement = null;

    const closeModal = (modal) => {
        if (!modal) return;

        modal.style.display = "none";
        modal.setAttribute("aria-hidden", "true");

        if (activeModal === modal) {
            activeModal = null;
        }

        if (
            modalTriggerElement &&
            typeof modalTriggerElement.focus === "function"
        ) {
            modalTriggerElement.focus();
        }

        modalTriggerElement = null;
    };

    const openModal = (modal, trigger) => {
        if (!modal) return;

        activeModal = modal;
        modalTriggerElement = trigger || null;

        modal.style.display = "flex";
        modal.setAttribute("aria-hidden", "false");

        const firstFocusable = modal.querySelector(
            [
                "button:not([disabled])",
                "[href]",
                "input:not([disabled])",
                "select:not([disabled])",
                "textarea:not([disabled])",
                '[tabindex]:not([tabindex="-1"])'
            ].join(",")
        );

        if (firstFocusable) {
            firstFocusable.focus();
        }
    };

    const modalTriggers =
        document.querySelectorAll("[data-modal-target]");

    modalTriggers.forEach((trigger) => {
        trigger.addEventListener("click", (event) => {
            event.preventDefault();

            const targetId =
                trigger.getAttribute("data-modal-target");

            if (!targetId) return;

            const modal =
                document.getElementById(targetId);

            openModal(modal, trigger);
        });
    });

    const modalCloses =
        document.querySelectorAll("[data-modal-close]");

    modalCloses.forEach((button) => {
        button.addEventListener("click", () => {
            const modal =
                button.closest(".modal-backdrop");

            closeModal(modal);
        });
    });

    document
        .querySelectorAll(".modal-backdrop")
        .forEach((modal) => {
            modal.setAttribute("aria-hidden", "true");

            modal.addEventListener("click", (event) => {
                if (event.target === modal) {
                    closeModal(modal);
                }
            });
        });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && activeModal) {
            closeModal(activeModal);
        }
    });
});