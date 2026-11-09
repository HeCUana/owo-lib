package io.wispforest.uwu.items;

import io.wispforest.owo.braid.core.Alignment;
import io.wispforest.owo.braid.core.AppState;
import io.wispforest.owo.braid.core.BraidScreen;
import io.wispforest.owo.braid.core.BraidScreenSettings;
import io.wispforest.owo.braid.core.Color;
import io.wispforest.owo.braid.core.Insets;
import io.wispforest.owo.braid.core.Size;
import io.wispforest.owo.braid.display.BraidDisplay;
import io.wispforest.owo.braid.display.BraidDisplayBinding;
import io.wispforest.owo.braid.display.DisplayQuad;
import io.wispforest.owo.braid.framework.BuildContext;
import io.wispforest.owo.braid.framework.proxy.WidgetState;
import io.wispforest.owo.braid.framework.widget.StatefulWidget;
import io.wispforest.owo.braid.framework.widget.StatelessWidget;
import io.wispforest.owo.braid.framework.widget.Widget;
import io.wispforest.owo.braid.widgets.Navigator;
import io.wispforest.owo.braid.widgets.basic.*;
import io.wispforest.owo.braid.widgets.button.Button;
import io.wispforest.owo.braid.widgets.button.MessageButton;
import io.wispforest.owo.braid.widgets.flex.*;
import io.wispforest.owo.braid.widgets.label.Label;
import io.wispforest.owo.braid.widgets.label.LabelStyle;
import io.wispforest.owo.braid.widgets.object.ItemStackWidget;
import io.wispforest.owo.braid.widgets.object.entity.EntityDisplayMode;
import io.wispforest.owo.braid.widgets.object.entity.EntityWidget;
import io.wispforest.owo.braid.widgets.stack.Stack;
import io.wispforest.owo.braid.widgets.stack.StackBase;
import io.wispforest.uwu.client.braid.TestSelector;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.util.CommonColors;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;

import java.util.List;

/**
 * Client-only half of {@link UwuBraidItem}.
 *
 * <p>Everything that touches {@code BraidScreen} / {@code Minecraft} / the braid widget tree lives
 * here so that {@code UwuBraidItem} stays loadable on a dedicated server. A member of
 * {@code UwuBraidItem} that referenced a client-only type would make the JVM resolve that class
 * while the item class is being initialized, which fails on a server with
 * {@code Cannot load class net.minecraft.client.gui.screens.Screen in environment type SERVER}.
 */
@Environment(EnvType.CLIENT)
public final class UwuBraidClient {

    private UwuBraidClient() {}

    private static BraidDisplay display;

    public static BraidDisplay display() {
        return display;
    }

    public static void setDisplay(BraidDisplay display) {
        UwuBraidClient.display = display;
    }

    public static void openTestSelector() {
        var settings = new BraidScreenSettings();
        settings.shouldPause = false;

        Minecraft.getInstance().gui.setScreen(new BraidScreen(settings, new TestSelector()));
    }

    public static void openDisplay(Player user) {
        if (display == null) {
            display = new BraidDisplay(
                new DisplayQuad(Vec3.ZERO, new Vec3(5, 0, 0), new Vec3(0, -3, 0)),
                750,
                450,
                new DisplayApp()
            ).renderAutomatically();

            BraidDisplayBinding.activate(display);
        }

        var right = new Vec3(-5, 0, 0)
            .xRot((float) Math.toRadians(-user.getXRot()))
            .yRot((float) Math.toRadians(-user.getYRot()));

        var down = new Vec3(0, -3, 0)
            .xRot((float) Math.toRadians(-user.getXRot()))
            .yRot((float) Math.toRadians(-user.getYRot()));

        display.quad = new DisplayQuad(
            user.getEyePosition()
                .add(user.getForward().scale(2.5))
                .subtract(right.scale(.5))
                .subtract(down.scale(.5)),
            right, down
        );
    }

    public static void closeDisplay() {
        Minecraft.getInstance().schedule(() -> {
            BraidDisplayBinding.deactivate(display);

            display.app.dispose();
            display = null;
        });
    }

    public record Tooltip() implements net.minecraft.world.inventory.tooltip.TooltipComponent {}

    public static class DisplayApp extends StatelessWidget {
        @Override
        public Widget build(BuildContext context) {
            return new Stack(
                new StackBase(new Navigator(new DisplayAppRoute())),
                new Padding(
                    Insets.all(1),
                    new HoverableBuilder(
                        (hoverableContext, hovered) -> new Box(
                            hovered ? Color.rgb(CommonColors.BLUE) : Color.WHITE,
                            true
                        )
                    )
                )
            );
        }
    }

    public static class DisplayAppRoute extends StatelessWidget {
        @Override
        public Widget build(BuildContext context) {
            return new Center(
                new Stack(
                    new Column(
                        MainAxisAlignment.START,
                        CrossAxisAlignment.CENTER,
                        new Padding(Insets.vertical(4)),
                        List.of(
                            new Sized(
                                Size.square(96),
                                new Cow()
                            ),
                            new Panel(
                                Panel.VANILLA_DARK,
                                new Padding(
                                    Insets.all(10),
                                    new Label(Component.translatable("text.uwu.braid").append(Component.literal(" in world real??")))
                                )
                            ),
                            new IntrinsicHeight(
                                new Row(
                                    MainAxisAlignment.START,
                                    CrossAxisAlignment.CENTER,
                                    new Button(
                                        UwuBraidClient::openTestSelector,
                                        new Sized(
                                            16,
                                            16,
                                            new ItemStackWidget(UwuItems.BRAID.getDefaultInstance())
                                        )
                                    ),
                                    new Button(
                                        () -> Minecraft.getInstance().player.handleCreativeModeItemDrop(UwuItems.BRAID.getDefaultInstance()),
                                        new Label(
                                            LabelStyle.SHADOW,
                                            true,
                                            Component.translatable("text.uwu.braid").append(Component.literal(" button"))
                                        )
                                    )
                                )
                            ),
                            new MessageButton(
                                Component.literal("test selector"),
                                () -> {
                                    Navigator.push(context, new TestSelectorRoute());
                                }
                            )
                        )
                    ),
                    new Align(
                        Alignment.TOP_RIGHT,
                        new Padding(
                            Insets.all(4),
                            new MessageButton(
                                Component.literal("x"),
                                UwuBraidClient::closeDisplay
                            )
                        )
                    )
                )
            );
        }
    }

    public static class TestSelectorRoute extends StatelessWidget {
        @Override
        public Widget build(BuildContext context) {
            return new Column(
                MainAxisAlignment.START,
                CrossAxisAlignment.CENTER,
                new Flexible(
                    new TestSelector()
                ),
                new Align(
                    Alignment.BOTTOM,
                    new Row(
                        new MessageButton(
                            Component.literal("back"),
                            () -> Navigator.pop(context)
                        ),
                        new MessageButton(
                            Component.literal("inspector"),
                            () -> AppState.of(context).activateInspector()
                        )
                    )
                )
            );
        }
    }

    public static class Cow extends StatefulWidget {
        @Override
        public WidgetState<Cow> createState() {
            return new State();
        }

        public static class State extends WidgetState<Cow> {

            private Entity cow;

            @Override
            public void init() {
                this.cow = new net.minecraft.world.entity.animal.cow.Cow(EntityTypes.COW, Minecraft.getInstance().level);
                this.cow.setId(1_000_000 + (int) (Math.random() * 10000));
            }

            @Override
            public Widget build(BuildContext context) {
                return new EntityWidget(
                    1.35,
                    this.cow,
                    widget -> widget.displayMode(EntityDisplayMode.CURSOR)
                );
            }
        }
    }
}
