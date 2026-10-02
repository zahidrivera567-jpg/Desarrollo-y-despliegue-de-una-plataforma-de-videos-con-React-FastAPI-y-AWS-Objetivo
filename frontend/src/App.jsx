import React, { useState } from 'react';
import { Menu, Search, Home, Compass, Tv, Clock, ThumbsUp, Video, Flame, Music, Gamepad2, Radio } from 'lucide-react';
import './App.css';

// Base de datos detallada por sección
const videosData = {
  inicio: [
    { id: '1', title: 'Aprende React 19 en 15 Minutos', channel: 'Dev Mastery', views: '120k vistas', time: 'hace 2 días', thumbnail: 'https://picsum.photos/300/170?random=1' },
    { id: '2', title: 'Construyendo con Vite y React Router', channel: 'Code World', views: '45k vistas', time: 'hace 1 semana', thumbnail: 'https://picsum.photos/300/170?random=2' },
    { id: '3', title: 'Curso Completo de JavaScript', channel: 'JS Academy', views: '500k vistas', time: 'hace 1 mes', thumbnail: 'https://picsum.photos/300/170?random=3' },
    { id: '4', title: 'Novedades de Frontend y CSS Grid', channel: 'Tech News', views: '15k vistas', time: 'hace 5 horas', thumbnail: 'https://picsum.photos/300/170?random=4' }
  ],
  explorar: [
    { id: 'e1', title: 'Las tendencias tecnológicas de 2026', channel: 'Futuro Tech', views: '200k vistas', time: 'hace 1 día', thumbnail: 'https://picsum.photos/300/170?random=10' },
    { id: 'e2', title: 'Música Lo-Fi para Programar y Concentrarse', channel: 'Chill Beats', views: '1.2M vistas', time: 'En vivo', thumbnail: 'https://picsum.photos/300/170?random=11' },
    { id: 'e3', title: 'Gameplay Final Boss - Unreal Engine 5', channel: 'ProGamer', views: '89k vistas', time: 'hace 3 días', thumbnail: 'https://picsum.photos/300/170?random=12' }
  ],
  suscripciones: [
    { id: 's1', title: 'Novedades de React Router v7', channel: 'Dev Mastery', views: '34k vistas', time: 'hace 4 horas', thumbnail: 'https://picsum.photos/300/170?random=20' },
    { id: 's2', title: 'Optimizando el rendimiento web', channel: 'Code World', views: '18k vistas', time: 'hace 1 día', thumbnail: 'https://picsum.photos/300/170?random=21' }
  ],
  historial: [
    { id: 'h1', title: 'Curso Completo de JavaScript', channel: 'JS Academy', views: '500k vistas', time: 'Visto ayer', thumbnail: 'https://picsum.photos/300/170?random=3' }
  ],
  megusta: [
    { id: 'm1', title: 'Aprende React 19 en 15 Minutos', channel: 'Dev Mastery', views: '120k vistas', time: 'Guardado hace 2 días', thumbnail: 'https://picsum.photos/300/170?random=1' }
  ]
};

export default function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('inicio');

  // Obtener videos de la pestaña activa
  const currentVideos = videosData[activeTab] || [];

  // Filtrar según el término de búsqueda
  const filteredVideos = currentVideos.filter(video =>
    video.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    video.channel.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="app">
      {/* Navbar Superior */}
      <header className="header">
        <div className="logo-section">
          <Menu size={20} className="icon-button" />
          <div className="logo" onClick={() => { setActiveTab('inicio'); setSearchTerm(''); }}>
            <Video color="red" size={24} />
            <span>YouTube</span>
          </div>
        </div>

        <div className="search-section">
          <input
            type="text"
            className="search-input"
            placeholder="Buscar..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button className="search-button">
            <Search size={18} />
          </button>
        </div>

        <div style={{ width: '40px' }} />
      </header>

      <div className="main-layout">
        {/* Barra Lateral */}
        <aside className="sidebar">
          <div
            className={`sidebar-item ${activeTab === 'inicio' ? 'active' : ''}`}
            onClick={() => setActiveTab('inicio')}
          >
            <Home size={20} />
            <span>Inicio</span>
          </div>
          <div
            className={`sidebar-item ${activeTab === 'explorar' ? 'active' : ''}`}
            onClick={() => setActiveTab('explorar')}
          >
            <Compass size={20} />
            <span>Explorar</span>
          </div>
          <div
            className={`sidebar-item ${activeTab === 'suscripciones' ? 'active' : ''}`}
            onClick={() => setActiveTab('suscripciones')}
          >
            <Tv size={20} />
            <span>Suscripciones</span>
          </div>
          <hr style={{ borderColor: '#303030', margin: '8px 0' }} />
          <div
            className={`sidebar-item ${activeTab === 'historial' ? 'active' : ''}`}
            onClick={() => setActiveTab('historial')}
          >
            <Clock size={20} />
            <span>Historial</span>
          </div>
          <div
            className={`sidebar-item ${activeTab === 'megusta' ? 'active' : ''}`}
            onClick={() => setActiveTab('megusta')}
          >
            <ThumbsUp size={20} />
            <span>Me gusta</span>
          </div>
        </aside>

        {/* ÁREA DE CONTENIDO PERSONALIZADO */}
        <main className="content-area">
          {/* Header/Encabezado personalizado por pestaña */}
          {activeTab === 'explorar' && (
            <div className="explore-categories">
              <div className="category-chip"><Flame size={18} /> Tendencias</div>
              <div className="category-chip"><Music size={18} /> Música</div>
              <div className="category-chip"><Gamepad2 size={18} /> Videojuegos</div>
              <div className="category-chip"><Radio size={18} /> En vivo</div>
            </div>
          )}

          {activeTab === 'suscripciones' && (
            <div className="page-header">
              <h2>Últimos videos de tus canales suscritos</h2>
            </div>
          )}

          {activeTab === 'historial' && (
            <div className="page-header">
              <h2>Historial de reproducciones</h2>
            </div>
          )}

          {activeTab === 'megusta' && (
            <div className="page-header">
              <h2>Videos que te han gustado</h2>
            </div>
          )}

          {/* Grilla de Videos */}
          {filteredVideos.length === 0 ? (
            <div className="no-results">
              <p>No hay videos disponibles en esta sección o búsqueda.</p>
            </div>
          ) : (
            <div className="video-grid">
              {filteredVideos.map((video) => (
                <div key={video.id} className="video-card">
                  <div className="thumbnail-container">
                    <img src={video.thumbnail} alt={video.title} className="thumbnail" />
                  </div>
                  <div className="video-details">
                    <div className="channel-avatar" />
                    <div className="video-info">
                      <span className="video-title">{video.title}</span>
                      <span className="channel-name">{video.channel}</span>
                      <span className="video-stats">{video.views} • {video.time}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}