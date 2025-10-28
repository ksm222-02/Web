#include <websocketpp/config/asio_no_tls.hpp>
#include <websocketpp/server.hpp>

#include <iostream>
#include <set>
#include <string>
#include <mutex> 
#include <functional> 

typedef websocketpp::server<websocketpp::config::asio> server;
typedef websocketpp::connection_hdl connection_hdl; 
typedef std::set<connection_hdl, std::owner_less<connection_hdl>> connection_set;

class SignalingServer {
public:
    SignalingServer() {
        m_server.init_asio();

        using websocketpp::lib::placeholders::_1;
        using websocketpp::lib::placeholders::_2;
        using websocketpp::lib::bind;
        
        m_server.set_open_handler(bind(&SignalingServer::on_open, this, _1));
        m_server.set_close_handler(bind(&SignalingServer::on_close, this, _1));
        m_server.set_message_handler(bind(&SignalingServer::on_message, this, _1, _2));

        m_server.set_reuse_addr(true); 
    }

    void run(uint16_t port) {
        m_server.listen(port);
        std::cout << "시그널링 서버 시작 (ws://0.0.0.0:" << port << ")" << std::endl;
        m_server.start_accept();
        m_server.run();
    }

private:
    void on_open(connection_hdl hdl) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_connections.insert(hdl);
        std::cout << "클라이언트 접속. (현재 " << m_connections.size() << " 명)" << std::endl;
    }

    void on_close(connection_hdl hdl) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_connections.erase(hdl);
        std::cout << "클라이언트 접속 끊김. (현재 " << m_connections.size() << " 명)" << std::endl;
    }

    void on_message(connection_hdl hdl, server::message_ptr msg) {
        std::cout << "메시지 수신: " << msg->get_payload().substr(0, 50) << "..." << std::endl;
        
        std::lock_guard<std::mutex> lock(m_mutex);
        
        for (auto const& conn_hdl : m_connections) {

            if (!conn_hdl.owner_before(hdl) && !hdl.owner_before(conn_hdl)) {
                continue;
            }

            try {
                m_server.send(conn_hdl, msg->get_payload(), msg->get_opcode());
            } catch (websocketpp::exception const & e) {
                std::cerr << "메시지 전송 실패: " << e.what() << std::endl;
            }
        }
    }

    server m_server;
    connection_set m_connections;
    std::mutex m_mutex;
};

int main() {
    try {
        SignalingServer srv;
        srv.run(8765);
    } catch (websocketpp::exception const & e) {
        std::cerr << "치명적 오류: " << e.what() << std::endl;
    } catch (std::exception const & e) {
        std::cerr << "표준 오류: " << e.what() << std::endl;
    }
}