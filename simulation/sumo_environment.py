"""
SUMO Traffic Simulation Environment
Integrates with SUMO for traffic simulation and RL training
"""

import os
import sys
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time
import random

# Try to import SUMO libraries
try:
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    import traci
    import sumolib
    SUMO_AVAILABLE = True
except ImportError:
    SUMO_AVAILABLE = False
    print("Warning: SUMO/TraCI not available. Install SUMO or set SUMO_HOME environment variable.")


@dataclass
class SimulationState:
    """State from SUMO simulation"""
    vehicle_count: int
    queue_length: int
    waiting_time: float
    mean_speed: float
    throughput: int
    emergency_detected: bool
    emergency_lane: Optional[str]
    current_phase: int
    simulation_time: float


@dataclass
class SimulationMetrics:
    """Collected metrics from simulation"""
    total_vehicles: int
    total_waiting_time: float
    average_waiting_time: float
    average_queue_length: float
    throughput: int
    average_speed: float
    emergency_response_time: float
    simulation_duration: float


class SUMOEnvironment:
    """
    SUMO traffic simulation environment for RL training
    
    Provides:
    - 4-way intersection simulation
    - Vehicle generation
    - Signal control via TraCI
    - State observation
    - Reward calculation
    """
    
    # Traffic light phases (typical 4-way intersection)
    PHASES = {
        0: 'GGGgrrrrGGGgrrrr',  # N-S green
        1: 'yyyyrrrryyyyrrrr',  # N-S yellow
        2: 'rrrrGGGgrrrrGGGg',  # E-W green
        3: 'rrrryyyyrrrryyyy',  # E-W yellow
    }
    
    # Vehicle types
    VEHICLE_TYPES = ['car', 'bus', 'bike', 'truck', 'auto']
    
    def __init__(
        self,
        config_file: str = None,
        net_file: str = None,
        route_file: str = None,
        gui: bool = False,
        step_length: float = 1.0,
        yellow_time: int = 3,
        min_green: int = 10,
        max_green: int = 50
    ):
        """
        Initialize SUMO environment
        
        Args:
            config_file: Path to SUMO configuration file
            net_file: Path to network file
            route_file: Path to route file
            gui: Whether to use SUMO GUI
            step_length: Simulation step length (seconds)
            yellow_time: Yellow phase duration
            min_green: Minimum green time
            max_green: Maximum green time
        """
        if not SUMO_AVAILABLE:
            raise ImportError("SUMO/TraCI not available. Please install SUMO.")
            
        self.config_file = config_file
        self.net_file = net_file
        self.route_file = route_file
        self.gui = gui
        self.step_length = step_length
        self.yellow_time = yellow_time
        self.min_green = min_green
        self.max_green = max_green
        
        # Simulation state
        self.simulation_running = False
        self.current_phase = 0
        self.phase_duration = 0
        self.total_steps = 0
        
        # Intersection and edge IDs (set after network load)
        self.tls_id = None
        self.incoming_edges = []
        self.outgoing_edges = []
        
        # Metrics
        self.episode_waiting_time = 0
        self.episode_vehicles = 0
        self.episode_throughput = 0
        
    def _build_sumo_command(self) -> List[str]:
        """Build SUMO command line arguments"""
        sumo_binary = 'sumo-gui' if self.gui else 'sumo'
        
        cmd = [sumo_binary]
        
        if self.config_file:
            cmd.extend(['-c', self.config_file])
        else:
            if self.net_file:
                cmd.extend(['-n', self.net_file])
            if self.route_file:
                cmd.extend(['-r', self.route_file])
                
        cmd.extend([
            '--step-length', str(self.step_length),
            '--waiting-time-memory', '1000',
            '--no-step-log', 'true',
            '--no-warnings', 'true'
        ])
        
        return cmd
        
    def start(self, seed: int = None) -> SimulationState:
        """
        Start SUMO simulation
        
        Args:
            seed: Random seed for reproducibility
            
        Returns:
            Initial simulation state
        """
        cmd = self._build_sumo_command()
        
        if seed is not None:
            cmd.extend(['--seed', str(seed)])
            
        traci.start(cmd)
        self.simulation_running = True
        
        # Get traffic light IDs
        tls_ids = traci.trafficlight.getIDList()
        if tls_ids:
            self.tls_id = tls_ids[0]
            
        # Get controlled edges
        if self.tls_id:
            controlled_links = traci.trafficlight.getControlledLinks(self.tls_id)
            for link in controlled_links:
                if link:
                    edge = link[0][0].split('_')[0]
                    if edge not in self.incoming_edges:
                        self.incoming_edges.append(edge)
        
        # Reset episode metrics
        self.episode_waiting_time = 0
        self.episode_vehicles = 0
        self.episode_throughput = 0
        self.current_phase = 0
        self.phase_duration = 0
        self.total_steps = 0
        
        return self._get_state()
    
    def stop(self):
        """Stop SUMO simulation"""
        if self.simulation_running:
            traci.close()
            self.simulation_running = False
            
    def reset(self, seed: int = None) -> SimulationState:
        """
        Reset simulation
        
        Args:
            seed: Random seed
            
        Returns:
            Initial state
        """
        self.stop()
        return self.start(seed)
    
    def step(self, action: int) -> Tuple[SimulationState, float, bool, Dict]:
        """
        Execute one step in the simulation
        
        Args:
            action: Green time duration (10, 20, 30, or 40)
            
        Returns:
            Tuple of (next_state, reward, done, info)
        """
        if not self.simulation_running:
            raise RuntimeError("Simulation not running. Call start() first.")
        
        # Execute the green phase for the specified duration
        green_duration = max(self.min_green, min(action, self.max_green))
        
        # Set traffic light to green
        if self.tls_id:
            traci.trafficlight.setPhase(self.tls_id, self.current_phase)
        
        # Run simulation for green duration
        waiting_time_before = self._get_total_waiting_time()
        vehicles_before = self._get_departed_vehicles()
        
        for _ in range(int(green_duration / self.step_length)):
            traci.simulationStep()
            self.total_steps += 1
            
        # Yellow phase
        if self.tls_id:
            traci.trafficlight.setPhase(self.tls_id, (self.current_phase + 1) % 4)
            
        for _ in range(int(self.yellow_time / self.step_length)):
            traci.simulationStep()
            self.total_steps += 1
        
        # Update phase
        self.current_phase = (self.current_phase + 2) % 4
        
        # Get new state
        state = self._get_state()
        
        # Calculate reward
        waiting_time_after = self._get_total_waiting_time()
        vehicles_after = self._get_departed_vehicles()
        
        queue_length = state.queue_length
        waiting_time_change = waiting_time_after - waiting_time_before
        throughput = vehicles_after - vehicles_before
        
        reward = self._calculate_reward(queue_length, waiting_time_change, throughput)
        
        # Check if done
        done = traci.simulation.getMinExpectedNumber() <= 0
        
        # Update episode metrics
        self.episode_waiting_time += waiting_time_change
        self.episode_throughput += throughput
        
        info = {
            'queue_length': queue_length,
            'waiting_time': waiting_time_change,
            'throughput': throughput,
            'phase': self.current_phase,
            'step': self.total_steps
        }
        
        return state, reward, done, info
    
    def _get_state(self) -> SimulationState:
        """Get current simulation state"""
        vehicle_count = traci.vehicle.getIDCount()
        
        # Calculate queue length (vehicles with speed < 0.1)
        queue_length = 0
        total_waiting = 0
        speeds = []
        emergency_detected = False
        emergency_lane = None
        
        for veh_id in traci.vehicle.getIDList():
            speed = traci.vehicle.getSpeed(veh_id)
            speeds.append(speed)
            
            if speed < 0.1:
                queue_length += 1
                
            total_waiting += traci.vehicle.getWaitingTime(veh_id)
            
            # Check for emergency vehicles
            veh_type = traci.vehicle.getTypeID(veh_id)
            if veh_type in ['emergency', 'ambulance', 'police', 'firetruck']:
                emergency_detected = True
                emergency_lane = traci.vehicle.getLaneID(veh_id)
        
        mean_speed = np.mean(speeds) if speeds else 0
        
        return SimulationState(
            vehicle_count=vehicle_count,
            queue_length=queue_length,
            waiting_time=total_waiting,
            mean_speed=mean_speed,
            throughput=self.episode_throughput,
            emergency_detected=emergency_detected,
            emergency_lane=emergency_lane,
            current_phase=self.current_phase,
            simulation_time=traci.simulation.getTime()
        )
    
    def _get_total_waiting_time(self) -> float:
        """Get total waiting time for all vehicles"""
        total = 0
        for veh_id in traci.vehicle.getIDList():
            total += traci.vehicle.getWaitingTime(veh_id)
        return total
    
    def _get_departed_vehicles(self) -> int:
        """Get number of vehicles that have completed their trip"""
        return traci.simulation.getArrivedNumber()
    
    def _calculate_reward(
        self,
        queue_length: int,
        waiting_time: float,
        throughput: int
    ) -> float:
        """
        Calculate reward for RL agent
        
        Reward = -(α₁ × queue_length + α₂ × waiting_time) + β × throughput
        
        Args:
            queue_length: Current queue length
            waiting_time: Change in waiting time
            throughput: Vehicles that completed trip
            
        Returns:
            Reward value
        """
        alpha1 = 1.0  # Queue weight
        alpha2 = 0.5  # Waiting time weight
        beta = 0.5    # Throughput bonus
        
        reward = -(alpha1 * queue_length + alpha2 * waiting_time) + beta * throughput
        
        return reward
    
    def get_metrics(self) -> SimulationMetrics:
        """Get collected metrics from current episode"""
        state = self._get_state()
        
        return SimulationMetrics(
            total_vehicles=self.episode_vehicles,
            total_waiting_time=self.episode_waiting_time,
            average_waiting_time=self.episode_waiting_time / max(1, self.total_steps),
            average_queue_length=state.queue_length,
            throughput=self.episode_throughput,
            average_speed=state.mean_speed,
            emergency_response_time=0,  # Would need tracking
            simulation_duration=state.simulation_time
        )
    
    def set_traffic_light(self, phase: int, duration: int = None):
        """
        Manually set traffic light phase
        
        Args:
            phase: Phase index (0-3)
            duration: Optional duration
        """
        if self.tls_id:
            traci.trafficlight.setPhase(self.tls_id, phase)
            if duration:
                traci.trafficlight.setPhaseDuration(self.tls_id, duration)
                
    def add_vehicle(
        self,
        route_id: str,
        vehicle_type: str = 'car',
        depart_time: float = None
    ) -> str:
        """
        Add vehicle to simulation
        
        Args:
            route_id: Route ID
            vehicle_type: Vehicle type
            depart_time: Departure time
            
        Returns:
            Vehicle ID
        """
        veh_id = f"veh_{self.episode_vehicles}"
        depart = depart_time or traci.simulation.getTime()
        
        traci.vehicle.add(
            vehID=veh_id,
            routeID=route_id,
            typeID=vehicle_type,
            depart=depart
        )
        
        self.episode_vehicles += 1
        return veh_id


class SUMOConfigGenerator:
    """
    Generate SUMO configuration files for a 4-way intersection
    """
    
    @staticmethod
    def generate_network(output_dir: str) -> str:
        """
        Generate a simple 4-way intersection network
        
        Args:
            output_dir: Output directory
            
        Returns:
            Path to generated network file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Node file
        nodes_content = """<?xml version="1.0" encoding="UTF-8"?>
<nodes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/nodes_file.xsd">
    <node id="center" x="0" y="0" type="traffic_light"/>
    <node id="north" x="0" y="100"/>
    <node id="south" x="0" y="-100"/>
    <node id="east" x="100" y="0"/>
    <node id="west" x="-100" y="0"/>
</nodes>"""
        
        nodes_file = os.path.join(output_dir, 'intersection.nod.xml')
        with open(nodes_file, 'w') as f:
            f.write(nodes_content)
        
        # Edge file
        edges_content = """<?xml version="1.0" encoding="UTF-8"?>
<edges xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/edges_file.xsd">
    <edge id="north_to_center" from="north" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_north" from="center" to="north" numLanes="2" speed="13.89"/>
    <edge id="south_to_center" from="south" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_south" from="center" to="south" numLanes="2" speed="13.89"/>
    <edge id="east_to_center" from="east" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_east" from="center" to="east" numLanes="2" speed="13.89"/>
    <edge id="west_to_center" from="west" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_west" from="center" to="west" numLanes="2" speed="13.89"/>
</edges>"""
        
        edges_file = os.path.join(output_dir, 'intersection.edg.xml')
        with open(edges_file, 'w') as f:
            f.write(edges_content)
        
        # Generate network using netconvert
        net_file = os.path.join(output_dir, 'intersection.net.xml')
        
        # Try to run netconvert
        try:
            import subprocess
            subprocess.run([
                'netconvert',
                '-n', nodes_file,
                '-e', edges_file,
                '-o', net_file
            ], check=True)
        except:
            # Create a placeholder if netconvert not available
            print("netconvert not available. Creating placeholder network file.")
            with open(net_file, 'w') as f:
                f.write('<!-- Placeholder network file. Run netconvert to generate proper file. -->')
        
        return net_file
    
    @staticmethod
    def generate_routes(
        output_dir: str,
        duration: int = 3600,
        vehicles_per_hour: int = 500
    ) -> str:
        """
        Generate route file with vehicle flows
        
        Args:
            output_dir: Output directory
            duration: Simulation duration (seconds)
            vehicles_per_hour: Vehicle generation rate
            
        Returns:
            Path to route file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        routes_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    <!-- Vehicle types -->
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" maxSpeed="50"/>
    <vType id="bus" accel="1.2" decel="4.0" sigma="0.5" length="12" maxSpeed="40"/>
    <vType id="truck" accel="1.0" decel="4.0" sigma="0.5" length="10" maxSpeed="35"/>
    <vType id="bike" accel="1.2" decel="3.0" sigma="0.5" length="2" maxSpeed="25"/>
    <vType id="auto" accel="2.0" decel="4.0" sigma="0.5" length="3" maxSpeed="40"/>
    <vType id="emergency" accel="3.0" decel="5.0" sigma="0.2" length="6" maxSpeed="60" vClass="emergency"/>
    
    <!-- Routes -->
    <route id="north_south" edges="north_to_center center_to_south"/>
    <route id="south_north" edges="south_to_center center_to_north"/>
    <route id="east_west" edges="east_to_center center_to_west"/>
    <route id="west_east" edges="west_to_center center_to_east"/>
    <route id="north_east" edges="north_to_center center_to_east"/>
    <route id="north_west" edges="north_to_center center_to_west"/>
    <route id="south_east" edges="south_to_center center_to_east"/>
    <route id="south_west" edges="south_to_center center_to_west"/>
    <route id="east_north" edges="east_to_center center_to_north"/>
    <route id="east_south" edges="east_to_center center_to_south"/>
    <route id="west_north" edges="west_to_center center_to_north"/>
    <route id="west_south" edges="west_to_center center_to_south"/>
    
    <!-- Traffic flows -->
    <flow id="flow_ns" type="car" route="north_south" begin="0" end="{duration}" 
          vehsPerHour="{vehicles_per_hour // 4}" departSpeed="max"/>
    <flow id="flow_sn" type="car" route="south_north" begin="0" end="{duration}" 
          vehsPerHour="{vehicles_per_hour // 4}" departSpeed="max"/>
    <flow id="flow_ew" type="car" route="east_west" begin="0" end="{duration}" 
          vehsPerHour="{vehicles_per_hour // 4}" departSpeed="max"/>
    <flow id="flow_we" type="car" route="west_east" begin="0" end="{duration}" 
          vehsPerHour="{vehicles_per_hour // 4}" departSpeed="max"/>
    
    <!-- Occasional emergency vehicles -->
    <flow id="emergency_ns" type="emergency" route="north_south" begin="300" end="{duration}" 
          probability="0.001" departSpeed="max"/>
</routes>"""
        
        routes_file = os.path.join(output_dir, 'intersection.rou.xml')
        with open(routes_file, 'w') as f:
            f.write(routes_content)
        
        return routes_file
    
    @staticmethod
    def generate_config(
        output_dir: str,
        net_file: str,
        route_file: str,
        duration: int = 3600
    ) -> str:
        """
        Generate SUMO configuration file
        
        Args:
            output_dir: Output directory
            net_file: Network file path
            route_file: Route file path
            duration: Simulation duration
            
        Returns:
            Path to config file
        """
        config_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{net_file}"/>
        <route-files value="{route_file}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="{duration}"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
    </processing>
</configuration>"""
        
        config_file = os.path.join(output_dir, 'intersection.sumocfg')
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        return config_file


# Mock environment for testing without SUMO
class MockSUMOEnvironment:
    """
    Mock SUMO environment for testing without SUMO installed
    """
    
    def __init__(self, **kwargs):
        self.current_phase = 0
        self.total_steps = 0
        self.episode_vehicles = 0
        self.episode_throughput = 0
        self.episode_waiting_time = 0
        
    def start(self, seed=None) -> SimulationState:
        np.random.seed(seed)
        return self._get_state()
    
    def stop(self):
        pass
    
    def reset(self, seed=None) -> SimulationState:
        self.current_phase = 0
        self.total_steps = 0
        self.episode_vehicles = 0
        self.episode_throughput = 0
        self.episode_waiting_time = 0
        np.random.seed(seed)
        return self._get_state()
    
    def step(self, action: int) -> Tuple[SimulationState, float, bool, Dict]:
        # Simulate traffic dynamics
        base_queue = max(0, 10 - action // 10 + np.random.randint(-3, 4))
        waiting_time = base_queue * 2 + np.random.random() * 5
        throughput = np.random.randint(1, 5)
        
        self.total_steps += 1
        self.episode_throughput += throughput
        self.episode_waiting_time += waiting_time
        
        # Update phase
        self.current_phase = (self.current_phase + 2) % 4
        
        state = SimulationState(
            vehicle_count=np.random.randint(5, 20),
            queue_length=base_queue,
            waiting_time=waiting_time,
            mean_speed=np.random.uniform(5, 15),
            throughput=self.episode_throughput,
            emergency_detected=np.random.random() < 0.05,
            emergency_lane=None,
            current_phase=self.current_phase,
            simulation_time=self.total_steps
        )
        
        reward = -(base_queue + 0.5 * waiting_time) + 0.5 * throughput
        done = self.total_steps >= 100
        
        info = {
            'queue_length': base_queue,
            'waiting_time': waiting_time,
            'throughput': throughput,
            'phase': self.current_phase,
            'step': self.total_steps
        }
        
        return state, reward, done, info
    
    def _get_state(self) -> SimulationState:
        return SimulationState(
            vehicle_count=np.random.randint(5, 20),
            queue_length=np.random.randint(0, 10),
            waiting_time=np.random.uniform(0, 50),
            mean_speed=np.random.uniform(5, 15),
            throughput=self.episode_throughput,
            emergency_detected=False,
            emergency_lane=None,
            current_phase=self.current_phase,
            simulation_time=self.total_steps
        )
    
    def get_metrics(self) -> SimulationMetrics:
        return SimulationMetrics(
            total_vehicles=self.episode_vehicles,
            total_waiting_time=self.episode_waiting_time,
            average_waiting_time=self.episode_waiting_time / max(1, self.total_steps),
            average_queue_length=5,
            throughput=self.episode_throughput,
            average_speed=10,
            emergency_response_time=0,
            simulation_duration=self.total_steps
        )


def get_environment(use_sumo: bool = True, **kwargs):
    """
    Get appropriate environment (SUMO or Mock)
    
    Args:
        use_sumo: Whether to use real SUMO
        **kwargs: Environment arguments
        
    Returns:
        Environment instance
    """
    if use_sumo and SUMO_AVAILABLE:
        return SUMOEnvironment(**kwargs)
    else:
        return MockSUMOEnvironment(**kwargs)


if __name__ == '__main__':
    # Test with mock environment
    print("Testing with Mock SUMO Environment...")
    
    env = MockSUMOEnvironment()
    state = env.start(seed=42)
    
    print(f"Initial state: vehicles={state.vehicle_count}, queue={state.queue_length}")
    
    total_reward = 0
    for i in range(50):
        action = random.choice([10, 20, 30, 40])
        state, reward, done, info = env.step(action)
        total_reward += reward
        
        if i % 10 == 0:
            print(f"Step {i}: action={action}, reward={reward:.2f}, queue={state.queue_length}")
        
        if done:
            break
    
    print(f"\nTotal reward: {total_reward:.2f}")
    print(f"Metrics: {env.get_metrics()}")
