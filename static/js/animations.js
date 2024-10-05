document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.addEventListener('mouseover', () => {
            button.style.transition = 'transform 0.2s';
            button.style.transform = 'scale(1.05)';
        });

        button.addEventListener('mouseout', () => {
            button.style.transform = 'scale(1)';
        });
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const createBtn = document.getElementById('create-document-btn');
    const form = document.getElementById('document-form');

    // Exibe o formulário quando o botão for clicado
    createBtn.addEventListener('click', () => {
        if (form.classList.contains('show-form')) {
            form.classList.remove('show-form');
        } else {
            form.classList.add('show-form');
        }
    });
});