import rclpy
from rclpy.node import Node
import time
import os

from nav_msgs.msg import Odometry 
from autoware_vehicle_msgs.msg import VelocityReport
from autoware_vehicle_msgs.msg import SteeringReport
from tier4_debug_msgs.msg import Float32Stamped
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS 
import threading

OUTPUT_FILE = 'autoware_metrics.log'
WEB_PORT = 5000

POSE_TOPIC = '/localization/kinematic_state'
VELOCITY_TOPIC = '/vehicle/status/velocity_status'
STEERING_TOPIC = '/vehicle/status/steering_status'
LIKELIHOOD_TOPIC = '/localization/pose_estimator/nearest_voxel_transformation_likelihood'
ACCURACY_TOPIC = '/localization_accuracy' 

app = Flask(__name__)
CORS(app, origins=["https://fml2.shop"])

class DataExtractorNode(Node):
    def __init__(self):
        super().__init__('autoware_data_extractor')
        
        self.data_lock = threading.Lock()
        
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_speed = 0.0
        self.current_steering = 0.0
        self.current_likelihood = 0.0
        self.current_accuracy = 0.0

        self.pose_sub = self.create_subscription(
            Odometry, POSE_TOPIC, self.pose_callback, 10)
            
        self.vel_sub = self.create_subscription(
            VelocityReport, VELOCITY_TOPIC, self.velocity_callback, 10)
        
        self.steering_sub = self.create_subscription(
            SteeringReport, STEERING_TOPIC, self.steering_callback, 10)

        self.likelihood_sub = self.create_subscription(
            Float32Stamped, LIKELIHOOD_TOPIC, self.likelihood_callback, 10)
            
        self.accuracy_sub = self.create_subscription(
            Float32Stamped, ACCURACY_TOPIC, self.accuracy_callback, 10)
            
        try:
            self.file_writer = open(OUTPUT_FILE, 'a')
            if os.path.getsize(OUTPUT_FILE) == 0:
                self.file_writer.write("Time,X,Y,Speed_mps,Likelihood,Accuracy,Steering\n")
        except Exception as e:
            self.get_logger().error(f"로그 파일을 여는 데 실패했습니다: {e}")
            rclpy.shutdown()
            
        self.timer = self.create_timer(1.0, self.timer_callback)
        
        self.get_logger().info(f"'{OUTPUT_FILE}'에 데이터 저장을 시작합니다.")
        self.get_logger().info(f"웹 서버가 http://0.0.0.0:{WEB_PORT} 에서 실행됩니다.")

    def get_current_data_json(self):
        with self.data_lock:
            data = {
                "time": time.strftime('%Y-%m-%d %H:%M:%S'),
                "x": self.current_x,
                "y": self.current_y,
                "speed_mps": self.current_speed,
                "likelihood": self.current_likelihood,
                "accuracy": self.current_accuracy,
                "steering": self.current_steering
            }
        return jsonify(data)

    def pose_callback(self, msg):
        with self.data_lock:
            self.current_x = msg.pose.pose.position.x
            self.current_y = msg.pose.pose.position.y

    def velocity_callback(self, msg):
        with self.data_lock:
            self.current_speed = msg.longitudinal_velocity

    def steering_callback(self, msg):
        with self.data_lock:
            self.current_steering = msg.steering_tire_angle

    def likelihood_callback(self, msg):
        with self.data_lock:
            self.current_likelihood = msg.data

    def accuracy_callback(self, msg):
        with self.data_lock:
            self.current_accuracy = msg.data

    def timer_callback(self):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        with self.data_lock:
            data_line = (
                f"{timestamp},"
                f"{self.current_x:.4f},"
                f"{self.current_y:.4f},"
                f"{self.current_speed:.4f},"
                f"{self.current_likelihood:.4f},"
                f"{self.current_accuracy:.4f},"
                f"{self.current_steering:.4f}"
            )
        
        try:
            self.file_writer.write(data_line + "\n")
            self.file_writer.flush()
        except Exception as e:
            self.get_logger().warn(f"로그 파일 쓰기 오류: {e}")
        
    def destroy_node(self):
        if hasattr(self, 'file_writer') and self.file_writer:
            self.file_writer.close()
            self.get_logger().info('로그 파일을 닫았습니다.')
        super().destroy_node()

def run_web_server(node):
    
    @app.route('/')
    def index():
        return send_from_directory('.', 'index.html')

    @app.route('/api/autoware')
    def get_status():
        return node.get_current_data_json()

    try:
        app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)
    except OSError as e:
        node.get_logger().error(f"웹 서버 실행 실패 (포트 {WEB_PORT}가 이미 사용 중일 수 있습니다): {e}")


def main(args=None):
    rclpy.init(args=args)
    node = DataExtractorNode()
    
    web_thread = threading.Thread(target=run_web_server, args=(node,), daemon=True)
    web_thread.start()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('키보드 인터럽트 (Ctrl+C)로 종료합니다.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
