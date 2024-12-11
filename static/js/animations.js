document.addEventListener('DOMContentLoaded', () => {
    // Animação para botões
    const buttons = document.querySelectorAll('button');
    if (buttons) {
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
                }, 100);
            });
        });
    }

    // Configurações para botões específicos
    configureButton('submit-btn', 'Enviando...', 'Enviar para Aprovação', 'Documento criado e enviado para aprovação!', '#2196F3', 'document-form');
    configureButton('cancel-btn', 'Enviando...', 'Cancelar Documento', 'Solicitação de cancelamento enviada!', '#FF5722', 'cancel-document-form');
    configureButton('review-btn', 'Enviando...', 'Revisar Documento', 'Documento enviado para revisão!', '#FFC107', 'review-document-form');
    configureButton('save-changes-btn', 'Salvando...', 'Salvar Alterações', 'Alterações salvas com sucesso!', '#4CAF50', 'edit-user-form', '/home' );
    configureButton('approve-btn', 'Enviando...', 'Aprovar', 'Aprovado com sucesso!', '#4CAF50', 'aprovar-reprovar-form', 'form-{{ tarefa.id }}');
    configureButton('reject-btn', 'Enviando...', 'Reprovar', 'Reprovado com sucesso!', '#FF5722', 'aprovar-reprovar-form', 'form-{{ tarefa.id }}');

    /**
     * Configura botões com mensagens e formulários específicos
     * @param {string} buttonId - ID do botão
     * @param {string} sendingText - Texto ao enviar
     * @param {string} defaultText - Texto padrão do botão
     * @param {string} messageText - Texto da mensagem exibida
     * @param {string} bgColor - Cor de fundo da mensagem
     * @param {string} formId - ID do formulário a ser enviado
     */
    
    // Configura botões com mensagens e formulários específicos
    function configureButton(buttonId, sendingText, defaultText, messageText, bgColor, formId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', (event) => {
                event.preventDefault(); // Impede o envio padrão do formulário momentaneamente

                // Atualiza o texto e desativa o botão
                button.innerHTML = sendingText;
                button.disabled = true;

                // Exibe a mensagem de confirmação
                const messageElement = document.createElement('div');
                messageElement.innerHTML = messageText;
                setMessageStyle(messageElement, bgColor);
                document.body.appendChild(messageElement);

                // Aguarda 2 segundos antes de submeter o formulário
                setTimeout(() => {
                    messageElement.remove(); // Remove a mensagem da tela
                    const form = document.getElementById(formId);
                    if (form) {
                        form.submit(); // Submete o formulário após o delay
                    } else {
                        console.error('Formulário não encontrado:', formId);
                    }
                }, 2000);
            });
        }
    }


    // Define estilo de mensagens
    function setMessageStyle(messageElement, bgColor) {
        messageElement.style.position = 'fixed';
        messageElement.style.top = '0';
        messageElement.style.left = '0';
        messageElement.style.width = '100vw';
        messageElement.style.height = '100vh';
        messageElement.style.display = 'flex';
        messageElement.style.justifyContent = 'center';
        messageElement.style.alignItems = 'center';
        messageElement.style.backgroundColor = `${bgColor}cc`; // Fundo com transparência
        messageElement.style.color = 'white';
        messageElement.style.padding = '20px';
        messageElement.style.borderRadius = '5px';
        messageElement.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';
        messageElement.style.zIndex = '9999';
        messageElement.style.textAlign = 'center';
    }

    

    // Funções para visualizar e resumir PDFs
    const app = {
        openModal: function () {
            const modal = document.getElementById('summary-modal');
            if (modal) {
                modal.style.display = 'flex';
                modal.style.justifyContent = 'center';
                modal.style.alignItems = 'center';
            }
        },
        closeModal: function () {
            const modal = document.getElementById('summary-modal');
            if (modal) {
                modal.style.display = 'none';
            }
        },
        viewPdf: function (url) {
            const pdfViewer = document.getElementById('app-pdf-viewer');
            if (pdfViewer) {
                pdfViewer.querySelector('iframe').src = url;
                pdfViewer.querySelector('h2').innerText = 'Visualizando PDF';
            }
        },
        summarizePdf: function (docId) {
            this.openModal();
            const summaryText = document.getElementById('summary-text');
            summaryText.innerText = 'Carregando...';

            fetch(`/summarize_pdf/${docId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.summary) {
                        summaryText.innerText = data.summary;
                    } else if (data.error) {
                        summaryText.innerText = `Erro: ${data.error}`;
                    }
                })
                .catch(err => {
                    summaryText.innerText = `Erro ao buscar o resumo: ${err.message}`;
                });
        }
    };

    // Adiciona `app` ao escopo global
    window.app = app;

    // Captura cliques nos links de resumo
    document.addEventListener('click', (event) => {
        const target = event.target.closest('.summarize-button');
        if (target) {
            event.preventDefault();
            const docId = target.getAttribute('data-doc-id');
            if (docId) {
                app.summarizePdf(docId);
            }
        }
    });
});
