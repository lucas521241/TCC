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

    // Adiciona animação ao botão de envio do formulário de criação
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.addEventListener('click', (event) => {
        event.preventDefault(); // Previne o envio do formulário para mostrar a animação
        submitBtn.innerHTML = 'Enviando...';
        submitBtn.disabled = true;

        // Cria o elemento de animação
        const distinctMessage = document.createElement('div');
        distinctMessage.innerHTML = 'Documento criado e enviado para aprovação!';
        distinctMessage.style.position = 'fixed';
        distinctMessage.style.top = '50%';
        distinctMessage.style.left = '50%';
        distinctMessage.style.transform = 'translate(-50%, -50%)';
        distinctMessage.style.backgroundColor = '#2196F3';
        distinctMessage.style.color = 'white';
        distinctMessage.style.padding = '20px';
        distinctMessage.style.borderRadius = '5px';
        distinctMessage.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';
        document.body.appendChild(distinctMessage);

        // Remove a mensagem após 3 segundos e reativa o botão
        setTimeout(() => {
            distinctMessage.remove();
            submitBtn.innerHTML = 'Enviar para Aprovação';
            submitBtn.disabled = false;
            document.getElementById('document-form').submit(); // Envia o formulário após a animação
        }, 3000);
    });

    // Adiciona animação ao botão de cancelamento
    const cancelBtn = document.getElementById('cancel-btn');
    cancelBtn.addEventListener('click', (event) => {
        event.preventDefault(); // Previne o envio do formulário para mostrar a animação
        cancelBtn.innerHTML = 'Enviando...';
        cancelBtn.disabled = true;

        // Cria o elemento de animação
        const cancelMessage = document.createElement('div');
        cancelMessage.innerHTML = 'Solicitação de cancelamento enviada!';
        cancelMessage.style.position = 'fixed';
        cancelMessage.style.top = '50%';
        cancelMessage.style.left = '50%';
        cancelMessage.style.transform = 'translate(-50%, -50%)';
        cancelMessage.style.backgroundColor = '#FF5722';
        cancelMessage.style.color = 'white';
        cancelMessage.style.padding = '20px';
        cancelMessage.style.borderRadius = '5px';
        cancelMessage.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';
        document.body.appendChild(cancelMessage);

        // Remove a mensagem após 3 segundos e reativa o botão
        setTimeout(() => {
            cancelMessage.remove();
            cancelBtn.innerHTML = 'Cancelar Documento';
            cancelBtn.disabled = false;
            document.getElementById('cancel-document-form').submit(); // Envia o formulário após a animação
        }, 3000);
    });

    // Adiciona animação ao botão de revisão
    const reviewBtn = document.getElementById('review-btn');
    reviewBtn.addEventListener('click', (event) => {
        event.preventDefault(); // Previne o envio do formulário para mostrar a animação
        reviewBtn.innerHTML = 'Enviando...';
        reviewBtn.disabled = true;

        // Cria o elemento de animação
        const reviewMessage = document.createElement('div');
        reviewMessage.innerHTML = 'Documento enviado para revisão!';
        reviewMessage.style.position = 'fixed';
        reviewMessage.style.top = '50%';
        reviewMessage.style.left = '50%';
        reviewMessage.style.transform = 'translate(-50%, -50%)';
        reviewMessage.style.backgroundColor = '#FFC107';
        reviewMessage.style.color = 'white';
        reviewMessage.style.padding = '20px';
        reviewMessage.style.borderRadius = '5px';
        reviewMessage.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';
        document.body.appendChild(reviewMessage);

        // Remove a mensagem após 3 segundos e reativa o botão
        setTimeout(() => {
            reviewMessage.remove();
            reviewBtn.innerHTML = 'Revisar Documento';
            reviewBtn.disabled = false;
            document.getElementById('review-document-form').submit(); // Envia o formulário após a animação
        }, 3000);
    });

    // Adiciona animação aos botões de aprovação e reprovação
    const approveButtons = document.querySelectorAll('.approve-button');
    const rejectButtons = document.querySelectorAll('.reject-button');

    approveButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault(); // Previne o envio do formulário para mostrar a animação
            showSuccessMessage('Processo aprovado!');
            button.closest('form').submit(); // Envia o formulário após a animação
        });
    });

    rejectButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault(); // Previne o envio do formulário para mostrar a animação
            showSuccessMessage('Processo reprovado!');
            button.closest('form').submit(); // Envia o formulário após a animação
        });
    });

    function showSuccessMessage(message) {
        // Cria o elemento de animação
        const successMessage = document.createElement('div');
        successMessage.innerHTML = message;
        successMessage.style.position = 'fixed';
        successMessage.style.top = '50%';
        successMessage.style.left = '50%';
        successMessage.style.transform = 'translate(-50%, -50%)';
        successMessage.style.backgroundColor = '#4CAF50';
        successMessage.style.color = 'white';
        successMessage.style.padding = '20px';
        successMessage.style.borderRadius = '5px';
        successMessage.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';
        document.body.appendChild(successMessage);

        // Remove a mensagem após 3 segundos
        setTimeout(() => {
            successMessage.remove();
        }, 3000);
    }
});
