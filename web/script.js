document.addEventListener('DOMContentLoaded', function () {
    const pageLinks = document.querySelectorAll('.page-link');
    const pages = document.querySelectorAll('.page');
    const navLinks = document.querySelectorAll('header .nav-link');
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const menuOpenIcon = document.getElementById('menu-open-icon');
    const menuCloseIcon = document.getElementById('menu-close-icon');

    function showPage(hash) {
        const targetHash = hash || '#home';
        let pageFound = false;

        pages.forEach(page => {
            if ('#' + page.id === targetHash) {
                page.classList.add('active');
                pageFound = true;
            } else {
                page.classList.remove('active');
            }
        });

        if (!pageFound) {
            document.getElementById('home').classList.add('active');
        }

        navLinks.forEach(link => {
            if (link.getAttribute('href') === targetHash) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
        
        // Close mobile menu after navigation
        mobileMenu.classList.add('hidden');
        document.body.style.overflow = '';
        menuOpenIcon.classList.remove('hidden');
        menuCloseIcon.classList.add('hidden');

        window.scrollTo(0, 0);
    }

    pageLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const targetHash = this.getAttribute('href');
            if(window.location.hash !== targetHash) {
                history.pushState(null, null, targetHash);
            }
            showPage(targetHash);
        });
    });
    
    window.addEventListener('popstate', function () {
        showPage(window.location.hash);
    });

    mobileMenuButton.addEventListener('click', function() {
        const isHidden = mobileMenu.classList.contains('hidden');
        mobileMenu.classList.toggle('hidden');
        menuOpenIcon.classList.toggle('hidden', !isHidden);
        menuCloseIcon.classList.toggle('hidden', isHidden);
        if (!isHidden) {
            document.body.style.overflow = '';
        } else {
            document.body.style.overflow = 'hidden';
        }
    });

    showPage(window.location.hash);
});