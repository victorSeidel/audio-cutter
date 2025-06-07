import os
import random
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox,
                            QFileDialog, QGroupBox, QMessageBox, QListWidget, QProgressBar,
                            QSlider)
from PyQt5.QtCore import Qt
from pydub import AudioSegment
from pydub.utils import which


class AudioCutterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cortador de Áudio em 0dB")
        self.setGeometry(100, 100, 650, 600)
        
        # Configurações padrão
        self.audio_path = ""
        self.output_dir = "cortes"
        self.prefixo = "audio"
        self.num_cortes = 30
        self.min_intervalo = 2.0  # minutos
        self.max_intervalo = 4.0  # minutos
        self.naming_format = "P" 
        self.silence_offset_ms = 0  # Offset após o ponto de silêncio (em ms)
        
        self.init_ui()
        
        # Forçar uso do ffmpeg local se existir
        if os.path.exists("ffmpeg.exe"):
            AudioSegment.converter = which("ffmpeg.exe")
    
    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Grupo: Arquivo de Entrada
        group_input = QGroupBox("Arquivo de Entrada")
        input_layout = QVBoxLayout()
        
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Selecione um arquivo de áudio...")
        btn_browse = QPushButton("Procurar...")
        btn_browse.clicked.connect(self.browse_audio)
        
        input_hbox = QHBoxLayout()
        input_hbox.addWidget(self.input_path)
        input_hbox.addWidget(btn_browse)
        
        input_layout.addLayout(input_hbox)
        group_input.setLayout(input_layout)
        
        # Grupo: Configurações de Corte
        group_settings = QGroupBox("Configurações de Corte")
        settings_layout = QVBoxLayout()
        
        # Prefixo
        hbox_prefix = QHBoxLayout()
        hbox_prefix.addWidget(QLabel("Nome para os arquivos:"))
        self.prefix_edit = QLineEdit(self.prefixo)
        hbox_prefix.addWidget(self.prefix_edit)
        
        # Formato de numeração
        hbox_naming = QHBoxLayout()
        hbox_naming.addWidget(QLabel("Formato de numeração:"))
        self.naming_edit = QLineEdit("P")
        self.naming_edit.setToolTip("Use 'P' para P01, 'p' para p01, ou outro caractere")
        hbox_naming.addWidget(self.naming_edit)
        
        # Número de cortes
        hbox_cuts = QHBoxLayout()
        hbox_cuts.addWidget(QLabel("Número de cortes:"))
        self.cut_spin = QSpinBox()
        self.cut_spin.setRange(1, 100)
        self.cut_spin.setValue(self.num_cortes)
        hbox_cuts.addWidget(self.cut_spin)
        
        # Intervalo mínimo/máximo
        hbox_interval = QHBoxLayout()
        hbox_interval.addWidget(QLabel("Intervalo mínimo (min):"))
        self.min_interval_spin = QDoubleSpinBox()
        self.min_interval_spin.setRange(0.5, 10.0)
        self.min_interval_spin.setValue(self.min_intervalo)
        hbox_interval.addWidget(self.min_interval_spin)
        
        hbox_interval.addWidget(QLabel("Intervalo máximo (min):"))
        self.max_interval_spin = QDoubleSpinBox()
        self.max_interval_spin.setRange(0.5, 10.0)
        self.max_interval_spin.setValue(self.max_intervalo)
        hbox_interval.addWidget(self.max_interval_spin)
        
        # Offset após silêncio
        hbox_offset = QHBoxLayout()
        hbox_offset.addWidget(QLabel("Offset após silêncio:"))
        
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-500, 500)  # -500ms a +500ms
        self.offset_slider.setValue(0)
        self.offset_slider.setTickInterval(100)
        self.offset_slider.setTickPosition(QSlider.TicksBelow)
        
        self.offset_label = QLabel("0 ms")
        self.offset_slider.valueChanged.connect(lambda: self.offset_label.setText(f"{self.offset_slider.value()} ms"))
        
        hbox_offset.addWidget(self.offset_slider)
        hbox_offset.addWidget(self.offset_label)
        
        # Pasta de saída
        hbox_output = QHBoxLayout()
        hbox_output.addWidget(QLabel("Pasta de saída:"))
        self.output_edit = QLineEdit(self.output_dir)
        btn_output_browse = QPushButton("Procurar...")
        btn_output_browse.clicked.connect(self.browse_output)
        hbox_output.addWidget(self.output_edit)
        hbox_output.addWidget(btn_output_browse)
        
        settings_layout.addLayout(hbox_prefix)
        settings_layout.addLayout(hbox_naming)
        settings_layout.addLayout(hbox_cuts)
        settings_layout.addLayout(hbox_interval)
        settings_layout.addLayout(hbox_offset)
        settings_layout.addLayout(hbox_output)
        group_settings.setLayout(settings_layout)
        
        # Progresso
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        
        # Lista de arquivos gerados
        self.file_list = QListWidget()
        self.file_list.setVisible(False)
        
        # Botão de processamento
        btn_process = QPushButton("Processar Áudio")
        btn_process.clicked.connect(self.process_audio)
        
        # Montar layout principal
        main_layout.addWidget(group_input)
        main_layout.addWidget(group_settings)
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.file_list)
        main_layout.addWidget(btn_process)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def browse_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecione o arquivo de áudio", "", 
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.flac)")
        
        if file_path:
            self.input_path.setText(file_path)
            self.audio_path = file_path
    
    def browse_output(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta de saída")
        
        if dir_path:
            self.output_edit.setText(dir_path)
            self.output_dir = dir_path
    
    def find_zero_crossings(self, audio_segment):
        """Encontra pontos onde ambos os canais estão próximos de 0dB"""
        zero_points = []
        samples = audio_segment.get_array_of_samples()
        frame_count = len(samples) // audio_segment.channels
        
        for i in range(frame_count):
            idx = i * audio_segment.channels
            left = samples[idx]
            right = samples[idx + 1] if audio_segment.channels > 1 else left
            
            # Verificar se ambos os canais estão próximos de 0
            if abs(left) < 100 and abs(right) < 100:  # Valor pequeno para considerar como "zero"
                zero_points.append(i * 1000 / audio_segment.frame_rate)  # Converter para ms
        
        return zero_points
    
    def process_audio(self):
        if not self.audio_path or not os.path.exists(self.audio_path):
            QMessageBox.critical(self, "Erro", "Selecione um arquivo de áudio válido!")
            return

        self.prefixo = self.prefix_edit.text()
        self.naming_format = self.naming_edit.text().strip() or "P"  # Usa "P" como padrão se vazio
        self.num_cortes = self.cut_spin.value()
        self.min_intervalo = self.min_interval_spin.value()
        self.max_intervalo = self.max_interval_spin.value()
        self.output_dir = self.output_edit.text()
        self.silence_offset_ms = self.offset_slider.value()  # Obtém o valor do offset

        min_interval_ms = int(self.min_intervalo * 60 * 1000)
        max_interval_ms = int(self.max_intervalo * 60 * 1000)

        try:
            audio = AudioSegment.from_file(self.audio_path)
            total_duration = len(audio)

            zero_points = self.find_zero_crossings(audio)
            if not zero_points:
                QMessageBox.critical(self, "Erro", "Não foram encontrados pontos com L e R em 0dB!")
                return

            self.progress.setVisible(True)
            self.progress.setMaximum(self.num_cortes)
            self.progress.setValue(0)
            os.makedirs(self.output_dir, exist_ok=True)
            self.file_list.clear()
            self.file_list.setVisible(True)

            # Gerar intervalos únicos e embaralhados
            possiveis_intervalos = list(set(
                random.randint(min_interval_ms, max_interval_ms)
                for _ in range(self.num_cortes * 2)  # tenta gerar mais para garantir variedade
            ))
            random.shuffle(possiveis_intervalos)
            intervalos = possiveis_intervalos[:self.num_cortes]

            # Cortes
            pontos_corte = [0]
            for intervalo in intervalos:
                proximo_ponto_estimado = pontos_corte[-1] + intervalo

                # Encontrar zero_point mais próximo após a posição estimada
                candidatos = [p for p in zero_points if p > proximo_ponto_estimado]
                if not candidatos:
                    break  # sem mais pontos de corte possíveis
                
                ponto_real = min(candidatos, key=lambda p: abs(p - proximo_ponto_estimado))
                
                # Aplicar o offset (pode ser positivo ou negativo)
                ponto_com_offset = ponto_real + self.silence_offset_ms
                
                # Garantir que não ultrapasse o fim do áudio
                if ponto_com_offset < total_duration:
                    pontos_corte.append(int(ponto_com_offset))
                else:
                    break

            if len(pontos_corte) - 1 < self.num_cortes:
                QMessageBox.warning(self, "Aviso", f"Apenas {len(pontos_corte)-1} cortes possíveis foram realizados.")
            
            for i in range(len(pontos_corte) - 1):
                inicio = pontos_corte[i]
                fim = pontos_corte[i + 1]
                corte = audio[inicio:fim]
                nome_arquivo = f"{self.prefixo} {self.naming_format}{i+1:02d}.mp3"
                output_path = os.path.join(self.output_dir, nome_arquivo)
                corte.export(output_path, format="mp3")
                self.file_list.addItem(nome_arquivo)
                self.progress.setValue(i + 1)
                QApplication.processEvents()

            QMessageBox.information(self, "Sucesso", f"{len(pontos_corte)-1} cortes realizados com sucesso!")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro:\n{str(e)}")
        finally:
            self.progress.setVisible(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioCutterApp()
    window.show()
    sys.exit(app.exec_())