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

        button.addEventListener('click', () => {
            button.style.transition = 'transform 0.1s';
            button.style.transform = 'scale(0.95)';
            setTimeout(() => {
                button.style.transform = 'scale(1)';
            }, 100); // Retorna ao tamanho normal após 100ms
        });
    });

    const createBtn = document.getElementById('create-document-btn');
    const form = document.getElementById('document-form');

    // Exibe o formulário quando o botão for clicado
    createBtn.addEventListener('click', () => {
        form.classList.toggle('show-form'); // Alterna a classe
        if (form.classList.contains('show-form')) {
            form.style.opacity = 0;
            form.style.display = 'flex'; // Garante que o formulário esteja visível
            setTimeout(() => {
                form.style.opacity = 1; // Faz uma animação de aparecimento
            }, 10); // Um pequeno atraso para permitir a transição de opacidade
        } else {
            form.style.opacity = 0; // Inicia a transição de desaparecimento
            setTimeout(() => {
                form.style.display = 'none'; // Esconde o formulário após a animação
            }, 300); // Tempo correspondente à duração da transição
        }
    });
});
