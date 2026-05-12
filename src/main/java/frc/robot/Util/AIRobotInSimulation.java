package frc.robot.Util;

import static edu.wpi.first.units.Units.Inches;
import static edu.wpi.first.units.Units.Kilograms;
import static edu.wpi.first.units.Units.Pounds;

import org.ironmaple.simulation.SimulatedArena;
import org.ironmaple.simulation.drivesims.SelfControlledSwerveDriveSimulation;
import org.ironmaple.simulation.drivesims.SwerveDriveSimulation;
import org.ironmaple.simulation.drivesims.configs.DriveTrainSimulationConfig;

import com.pathplanner.lib.auto.AutoBuilder;
import com.pathplanner.lib.commands.FollowPathCommand;
import com.pathplanner.lib.config.ModuleConfig;
import com.pathplanner.lib.config.PIDConstants;
import com.pathplanner.lib.config.RobotConfig;
import com.pathplanner.lib.controllers.PPHolonomicDriveController;
import com.pathplanner.lib.path.PathPlannerPath;

import edu.wpi.first.math.geometry.Pose2d;
import edu.wpi.first.math.geometry.Rotation2d;
import edu.wpi.first.math.geometry.Translation2d;
import edu.wpi.first.math.system.plant.DCMotor;
import edu.wpi.first.units.Units;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.SubsystemBase;

public class AIRobotInSimulation extends SubsystemBase {
    /* If an opponent robot is not on the field, it is placed in a queening position for performance. */
    public static final Pose2d[] ROBOT_QUEENING_POSITIONS = new Pose2d[] {
        new Pose2d(-6, 0, new Rotation2d()),
        new Pose2d(-5, 0, new Rotation2d()),
        new Pose2d(-4, 0, new Rotation2d()),
        new Pose2d(-3, 0, new Rotation2d()),
        new Pose2d(-2, 0, new Rotation2d())
    };

    private final SelfControlledSwerveDriveSimulation driveSimulation;
    private final Pose2d queeningPose;
    private final int id;

        // PathPlanner configuration
    private static final RobotConfig PP_CONFIG = new RobotConfig(
            55, // Robot mass in kg
            8,  // Robot MOI
            new ModuleConfig(
                    edu.wpi.first.math.util.Units.inchesToMeters(2), 3.5, 1.2, DCMotor.getFalcon500(1).withReduction(8.14), 60, 1), // Swerve module config
            0.6
    );

    // PathPlanner PID settings
    private final PPHolonomicDriveController driveController =
            new PPHolonomicDriveController(new PIDConstants(5.0, 0.02), new PIDConstants(7.0, 0.05));


    public AIRobotInSimulation(int id) {
        this.id = id;
        this.queeningPose = ROBOT_QUEENING_POSITIONS[id];
        this.driveSimulation = new SelfControlledSwerveDriveSimulation(new SwerveDriveSimulation(DriveTrainSimulationConfig.Default(), new Pose2d()));
        SimulatedArena.getInstance().addDriveTrainSimulation(
            driveSimulation.getDriveTrainSimulation()
        );

        
    }

    /** Follow path command for opponent robots */
    public Command opponentRobotFollowPath(PathPlannerPath path) {
        return new FollowPathCommand(
                path, // Specify the path
                // Provide actual robot pose in simulation, bypassing odometry error
                driveSimulation::getActualPoseInSimulationWorld,
                // Provide actual robot speed in simulation, bypassing encoder measurement error
                driveSimulation::getActualSpeedsRobotRelative,
                // Chassis speeds output
                (speeds, feedforwards) -> 
                    driveSimulation.runChassisSpeeds(speeds, new Translation2d(), false, false),
                driveController, // Specify PID controller
                PP_CONFIG,       // Specify robot configuration
                // Flip path based on alliance side
                () -> DriverStation.getAlliance()
                    .orElse(DriverStation.Alliance.Blue)
                    .equals(DriverStation.Alliance.Red),
                this // AIRobotInSimulation is a subsystem; this command should use it as a requirement
        );
    }
}