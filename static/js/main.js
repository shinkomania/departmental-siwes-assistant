/**
 * Departmental SIWES Assistant (DSA) - Client Javascript
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Menu Toggle
    const mobileToggle = document.querySelector('.mobile-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });
    }

    // 2. Nigerian Cities by State Map for smart dropdown autocomplete
    const stateCitiesMap = {
        'FCT Abuja': ['Abuja', 'Garki', 'Wuse', 'Maitama', 'Gudu', 'Jabi', 'Kubwa', 'Gwagwalada'],
        'Lagos': ['Lagos (Yaba)', 'Lagos (Ikeja)', 'Lagos (Lekki)', 'Lagos (Victoria Island)', 'Lagos Island', 'Surulere', 'Ikorodu'],
        'Kaduna': ['Kaduna', 'Zaria', 'Kafanchan', 'Sabon Gari'],
        'Kano': ['Kano', 'Bompai', 'Nassarawa', 'Fagge'],
        'Oyo': ['Ibadan', 'Ogbomoso', 'Oyo', 'Iseyin'],
        'Rivers': ['Port Harcourt', 'Obio-Akpor', 'Eleme', 'Bonny'],
        'Enugu': ['Enugu', 'Nsukka', 'Udi'],
        'Ogun': ['Abeokuta', 'Ota', 'Sagamu', 'Ijebu Ode'],
        'Edo': ['Benin City', 'Ekpoma', 'Auchi'],
        'Delta': ['Warri', 'Asaba', 'Ughelli', 'Sapele'],
        'Anambra': ['Awka', 'Onitsha', 'Nnewi'],
        'Plateau': ['Jos', 'Bukuru'],
        'Kwara': ['Ilorin', 'Offa'],
        'Akwa Ibom': ['Uyo', 'Eket', 'Ikot Ekpene'],
        'Cross River': ['Calabar', 'Ikom']
    };

    const stateSelect = document.getElementById('stateSelect') || document.querySelector('select[name="state"]') || document.querySelector('select[name="preferred_state"]');
    const cityInput = document.getElementById('cityInput') || document.querySelector('input[name="city"]') || document.querySelector('input[name="preferred_city"]');
    const cityDatalist = document.getElementById('cityList');

    if (stateSelect && cityDatalist) {
        stateSelect.addEventListener('change', () => {
            const selectedState = stateSelect.value;
            cityDatalist.innerHTML = '';
            
            if (stateCitiesMap[selectedState]) {
                stateCitiesMap[selectedState].forEach(city => {
                    const option = document.createElement('option');
                    option.value = city;
                    cityDatalist.appendChild(option);
                });
            }
        });
    }

    // 3. Auto dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-6px)';
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });

    // 4. Modal Open/Close helpers
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    modalTriggers.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const targetId = btn.getAttribute('data-modal-target');
            const modal = document.getElementById(targetId);
            if (modal) {
                modal.style.display = 'flex';
            }
        });
    });

    const modalCloses = document.querySelectorAll('[data-modal-close]');
    modalCloses.forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal-backdrop');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });
});
